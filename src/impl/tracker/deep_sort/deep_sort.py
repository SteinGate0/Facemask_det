import numpy as np
import torch

from .deep.feature_extractor import Extractor
from .sort.nn_matching import NearestNeighborDistanceMetric
from .sort.detection import Detection
from .sort.tracker import Tracker

import os
curr_path = os.path.split(os.path.abspath(__file__))[0]

__all__ = ['DeepSort']


class DeepSort(object):
    def __init__(self, model_path=None, class_filter=list(), max_dist=0.2, max_iou_distance=0.7, max_age=70, 
                    n_init=3, r_times=0, nn_budget=100, use_cuda=True, a_cleaning=None):
        if model_path is None:
            model_path = os.path.join(curr_path, "deep/checkpoint/ckpt.t7")
        self.extractor = Extractor(model_path, use_cuda=use_cuda)
        self.class_filter = class_filter
        self.r_times = r_times

        max_cosine_distance = max_dist
        metric = NearestNeighborDistanceMetric(
            "cosine", max_cosine_distance, nn_budget)
        self.tracker = Tracker(metric, max_iou_distance=max_iou_distance, max_age=max_age, \
                               n_init=n_init, a_cleaning=a_cleaning)


    def update(self, dets, task_name="", goods_in=None, ori_img=None):
        outputs = []
        goods_out = []
        if not goods_in:
            goods_in = [None] * len(dets)

        if task_name:
            if len(self.class_filter):
                temp_det = []
                temp_goods = []
                for i, d in enumerate(dets):
                    if d[5] in self.class_filter:
                        outputs.append(np.concatenate((d, [-1])).reshape(1,-1))
                        goods_out.append(goods_in[i])
                    else:
                        temp_det.append(d)
                        temp_goods.append(goods_in[i])
                if temp_det:
                    dets = np.asarray(temp_det)
                else:
                    dets = np.empty((0, 6))
                goods_in = temp_goods

            bbox_xywh = self.xyxy2xywh(dets[:, :4])
            confidences = dets[:, 4]
            classes = dets[:, 5]
            self.height, self.width = ori_img.shape[:2]
            # generate detections
            features = self._get_features(bbox_xywh, ori_img)
            bbox_tlwh = self._xywh_to_tlwh(bbox_xywh)
            detections = [Detection(bbox_tlwh[i], classes[i], conf, features[i]) for i, conf in enumerate(confidences)]

            # update tracker
            self.tracker.update(detections, goods_in, task_name)

            # output bbox identities
            for track in self.tracker.tracks_dict.get(task_name, list())[0]:
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

    """
    TODO:
        Convert bbox from xc_yc_w_h to xtl_ytl_w_h
    Thanks JieChen91@github.com for reporting this bug!
    """
    @staticmethod
    def _xywh_to_tlwh(bbox_xywh):
        if isinstance(bbox_xywh, np.ndarray):
            bbox_tlwh = bbox_xywh.copy()
        elif isinstance(bbox_xywh, torch.Tensor):
            bbox_tlwh = bbox_xywh.clone()
        bbox_tlwh[:, 0] = bbox_xywh[:, 0] - bbox_xywh[:, 2] / 2.
        bbox_tlwh[:, 1] = bbox_xywh[:, 1] - bbox_xywh[:, 3] / 2.
        return bbox_tlwh

    def _xywh_to_xyxy(self, bbox_xywh):
        x, y, w, h = bbox_xywh
        x1 = max(int(x - w / 2), 0)
        x2 = min(int(x + w / 2), self.width - 1)
        y1 = max(int(y - h / 2), 0)
        y2 = min(int(y + h / 2), self.height - 1)
        return x1, y1, x2, y2

    def _tlwh_to_xyxy(self, bbox_tlwh):
        """
        TODO:
            Convert bbox from xtl_ytl_w_h to xc_yc_w_h
        Thanks JieChen91@github.com for reporting this bug!
        """
        x, y, w, h = bbox_tlwh
        x1 = max(int(x), 0)
        x2 = min(int(x+w), self.width - 1)
        y1 = max(int(y), 0)
        y2 = min(int(y+h), self.height - 1)
        return x1, y1, x2, y2

    def increment_ages(self):
        self.tracker.increment_ages()

    def _xyxy_to_tlwh(self, bbox_xyxy):
        x1, y1, x2, y2 = bbox_xyxy

        t = x1
        l = y1
        w = int(x2 - x1)
        h = int(y2 - y1)
        return t, l, w, h

    def _get_features(self, bbox_xywh, ori_img):
        im_crops = []
        for box in bbox_xywh:
            x1, y1, x2, y2 = self._xywh_to_xyxy(box)
            im = ori_img[y1:y2, x1:x2]
            im_crops.append(im)
        if im_crops:
            features = self.extractor(im_crops)
        else:
            features = np.array([])
        return features

    def xyxy2xywh(self, x):
        # Convert nx4 boxes from [x1, y1, x2, y2] to [x, y, w, h] where xy1=top-left, xy2=bottom-right
        y = torch.zeros_like(x) if isinstance(x, torch.Tensor) else np.zeros_like(x)
        y[:, 0] = (x[:, 0] + x[:, 2]) / 2  # x center
        y[:, 1] = (x[:, 1] + x[:, 3]) / 2  # y center
        y[:, 2] = x[:, 2] - x[:, 0]  # width
        y[:, 3] = x[:, 3] - x[:, 1]  # height
        return y