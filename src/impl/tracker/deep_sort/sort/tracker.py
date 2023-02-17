# vim: expandtab:ts=4:sw=4
from __future__ import absolute_import
import numpy as np
import time
import threading
import logging
from . import kalman_filter
from . import linear_assignment
from . import iou_matching
from .track import Track


class Tracker:
    """
    This is the multi-target tracker.

    Parameters
    ----------
    metric : nn_matching.NearestNeighborDistanceMetric
        A distance metric for measurement-to-track association.
    max_age : int
        Maximum number of missed misses before a track is deleted.
    n_init : int
        Number of consecutive detections before the track is confirmed. The
        track state is set to `Deleted` if a miss occurs within the first
        `n_init` frames.

    Attributes
    ----------
    metric : nn_matching.NearestNeighborDistanceMetric
        The distance metric used for measurement to track association.
    max_age : int
        Maximum number of missed misses before a track is deleted.
    n_init : int
        Number of frames that a track remains in initialization phase.
    kf : kalman_filter.KalmanFilter
        A Kalman filter to filter target trajectories in image space.
    tracks : List[Track]
        The list of active tracks at the current time step.

    """

    def __init__(self, metric, max_iou_distance=0.7, max_age=70, n_init=3, a_cleaning=None):
        self.metric = metric
        self.max_iou_distance = max_iou_distance
        self.max_age = max_age
        self.n_init = n_init

        self.kf = kalman_filter.KalmanFilter()
        self.tracks_dict = {}

        if isinstance(a_cleaning, object):
            a_cleaning.mp_watcher_list.append(self.tracks_dict)

        self.logger = logging.getLogger("root.tracker.deep_sort")


    def increment_ages(self, tracks):
        for track in tracks:
            track.increment_age()
            track.mark_missed()

    def update(self, detections, goods_in, task_name):
        """Perform measurement update and track management.

        Parameters
        ----------
        detections : List[deep_sort.detection.Detection]
            A list of detections at the current time step.

        """
        tracks, info = self.tracks_dict.setdefault(task_name, [[],[1]])
        # predict
        for track in tracks:
            track.predict(self.kf)

        # Run matching cascade.
        matches, unmatched_tracks, unmatched_detections = \
            self._match(detections, tracks)

        # Update track set.
        for track_idx, detection_idx in matches:
            tracks[track_idx].update(
                self.kf, detections[detection_idx], goods_in[detection_idx])
        for track_idx in unmatched_tracks:
            tracks[track_idx].mark_missed()
        for detection_idx in unmatched_detections:
            self._initiate_track(detections[detection_idx], goods_in[detection_idx], tracks, info)

        # Remove deleted tracks.
        i = len(tracks)
        for t in reversed(tracks):
            i -= 1
            if t.is_deleted():
                tracks.pop(i)

        # Update distance metric.
        active_targets = [t.track_id for t in tracks if t.is_confirmed()]
        features, targets = [], []
        for track in tracks:
            if not track.is_confirmed():
                continue
            features += track.features
            targets += [track.track_id for _ in track.features]
            track.features = []
        self.metric.partial_fit(
            np.asarray(features), np.asarray(targets), active_targets)

    def _match(self, detections, tracks):

        def gated_metric(tracks, dets, track_indices, detection_indices):
            features = np.array([dets[i].feature for i in detection_indices])
            targets = np.array([tracks[i].track_id for i in track_indices])
            cost_matrix = self.metric.distance(features, targets)
            cost_matrix = linear_assignment.gate_cost_matrix(
                self.kf, cost_matrix, tracks, dets, track_indices,
                detection_indices)

            return cost_matrix

        # Split track set into confirmed and unconfirmed tracks.
        confirmed_tracks = [
            i for i, t in enumerate(tracks) if t.is_confirmed()]
        unconfirmed_tracks = [
            i for i, t in enumerate(tracks) if not t.is_confirmed()]

        # Associate confirmed tracks using appearance features.
        matches_a, unmatched_tracks_a, unmatched_detections = \
            linear_assignment.matching_cascade(
                gated_metric, self.metric.matching_threshold, self.max_age,
                tracks, detections, confirmed_tracks)

        # Associate remaining tracks together with unconfirmed tracks using IOU.
        iou_track_candidates = unconfirmed_tracks + [
            k for k in unmatched_tracks_a if
            tracks[k].time_since_update == 1]
        unmatched_tracks_a = [
            k for k in unmatched_tracks_a if
            tracks[k].time_since_update != 1]
        matches_b, unmatched_tracks_b, unmatched_detections = \
            linear_assignment.min_cost_matching(
                iou_matching.iou_cost, self.max_iou_distance, tracks,
                detections, iou_track_candidates, unmatched_detections)

        matches = matches_a + matches_b
        unmatched_tracks = list(set(unmatched_tracks_a + unmatched_tracks_b))
        return matches, unmatched_tracks, unmatched_detections

    def _initiate_track(self, detection, goods, tracks, info):
        mean, covariance = self.kf.initiate(detection.to_xyah())
        tracks.append(Track(
            mean, covariance, info[0], detection.classID, detection.confidence, goods, self.n_init, self.max_age,
            detection.feature))
        info[0] += 1