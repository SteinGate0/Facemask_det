import time
import numpy as np
import threading
import logging
from collections import deque

from .utils.linear_assignment import min_cost_matching, matching_cascade
from .utils.kalman_filter import KalmanFilter
from .utils.iou_matching import iou_cost
from .utils.track import Track
from .utils.detection import Detection


class Sort_v2:
    def __init__(self, class_filter=list(), max_iou_distance=0.7, max_age=30, n_init=5, r_times=0, a_cleaning=None):
        self.max_iou_dist = max_iou_distance
        self.max_age = max_age
        self.n_init = n_init
        self.r_times = r_times

        self.kf = KalmanFilter()
        self.tracks_dict = {}
        self.class_filter = class_filter

        if isinstance(a_cleaning, object):
            a_cleaning.mp_watcher_list.append(self.tracks_dict)  #[{}]

        self.logger = logging.getLogger("root.tracker.sort_v2")



    def update(self, dets, task_name="", goods_in=None, ori_img=None):
        outputs = []
        goods_out = []  #???输出的富余的信息，根据项目需要，例如识别人，还有人的骨架信息可以选择保留
        if not goods_in:
            goods_in = [None] * len(dets)

        if task_name:
            tracks, info = self.tracks_dict.setdefault(task_name, [[],[1]])
            print('task_name:',task_name,'tracks:',tracks,'info:',info)
            # 为task_name添加[[],[1]]   返回值tracks&info是啥
            if len(self.class_filter):
                temp_det = []
                temp_goods = []
                for i, d in enumerate(dets):
                    if d[5] in self.class_filter:
                        outputs.append(np.concatenate((d, [-1])).reshape(1,-1))  # 如果d[5]为要过滤掉的类，trackid = -1拼接， shape形:[1,7]
                        goods_out.append(goods_in[i])
                    else:
                        temp_det.append(d)
                        temp_goods.append(goods_in[i])
                if temp_det:
                    dets = np.asarray(temp_det)  # 将list转换为 ndarray
                else:
                    dets = np.empty((0, 6))
                goods_in = temp_goods

            bbox_tlbr = dets[:, :4]   # 坐标
            confidences = dets[:, 4]  # 置信度
            classes = dets[:, 5]      # 类别
            self.height, self.width = ori_img.shape[:2]

            detections = [Detection(bbox_tlbr[i], classes[i], conf) for i, conf in enumerate(confidences)]

            # predict
            for track in tracks:
                track.predict(self.kf)  # 如何索引到的predict方法，track是字典中包含的追踪器？

            # Run matching cascade.  运行匹配级联
            matches, unmatched_tracks, unmatched_detections = self._match(detections, tracks)

            # Update matched tracks set.
            for track_idx, detection_idx in matches:
                tracks[track_idx].update(self.kf, detections[detection_idx], goods_in[detection_idx]) # update方法
            # Update tracks that missing.
            for track_idx in unmatched_tracks:
                tracks[track_idx].mark_missed()
            # Create new detections track.
            for detection_idx in unmatched_detections:
                self._initiate_track(detections[detection_idx], goods_in[detection_idx], tracks, info)

            # Remove deleted tracks.
            i = len(tracks)
            for t in reversed(tracks):
                i -= 1
                if t.is_deleted():
                    tracks.pop(i)

            # output bbox identities
            for track in tracks:
                if not track.is_confirmed() or track.time_since_update > self.r_times:
                    continue
                box = track.to_tlwh()
                x1, y1, x2, y2 = self._tlwh_to_xyxy(box)
                track_id = track.track_id
                class_id = track.class_id
                conf = track.conf
                goods_out.append(track.goods)
                outputs.append(np.array([x1, y1, x2, y2, conf, class_id, track_id]).reshape(1,-1))
        else:
            for d in dets:
                outputs.append(np.concatenate((d, [-1])).reshape(1,-1))
            goods_out = goods_in
        if len(outputs) > 0:
            outputs = np.concatenate(outputs, axis=0)
        return outputs, goods_out

    def _match(self, detections, tracks):
        confirmed_tracks, unconfirmed_tracks = [], []
        for i, t in enumerate(tracks):
            if t.is_confirmed():
                confirmed_tracks.append(i)
            else:
                unconfirmed_tracks.append(i)

        matches_a, unmatched_tracks_a, unmatched_detections = matching_cascade(
            iou_cost, self.max_iou_dist, self.max_age, tracks, detections, confirmed_tracks
        )

        track_candidates = unconfirmed_tracks + [
            k for k in unmatched_tracks_a if tracks[k].time_since_update == 1]
        unmatched_tracks_a = [
            k for k in unmatched_tracks_a if tracks[k].time_since_update != 1]

        matches_b, unmatched_tracks_b, unmatched_detections = min_cost_matching(
            iou_cost, self.max_iou_dist, tracks, detections, track_candidates, unmatched_detections
        )

        matches = matches_a + matches_b
        unmatched_tracks = list(set(unmatched_tracks_a + unmatched_tracks_b))
        return matches, unmatched_tracks, unmatched_detections

    def _initiate_track(self, detection, goods, tracks, info):
        mean, covariance = self.kf.initiate(detection.to_xyah())
        tracks.append(Track(mean, covariance, info[0], detection.classID, detection.confidence, goods, self.n_init, self.max_age))
        info[0] += 1

    def _tlwh_to_xyxy(self, bbox_tlwh):
        x, y, w, h = bbox_tlwh
        x1 = max(int(x), 0)
        x2 = min(int(x+w), self.width - 1)
        y1 = max(int(y), 0)
        y2 = min(int(y+h), self.height - 1)
        return x1, y1, x2, y2
