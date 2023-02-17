# vim: expandtab:ts=4:sw=4
import numpy as np


class Detection(object):
    """
    This class represents a bounding box detection in a single image.
    这个类表示单个图像中的边界框检测。

    Parameters
    ----------
    tlwh : array_like
        Bounding box in format `(x, y, w, h)`.
    confidence : float
        Detector confidence score.

    Attributes
    ----------
    tlwh : ndarray
        Bounding box in format `(top left x, top left y, width, height)`.
    confidence : ndarray
        Detector confidence score.

    """

    def __init__(self, tlbr, classID, confidence):
        self.tlbr = tlbr
        self.classID = classID
        self.confidence = float(confidence)

    def to_tlwh(self):
        """Get (top, left, width, height).
        """
        ret = self.tlbr.copy()
        ret[2:] = ret[2:] - ret[:2]
        return ret

    def to_xyah(self):
        """Get (x_center, y_center, aspect ratio, height).
        """
        ret = self.to_tlwh()
        ret[:2] += ret[2:] / 2
        ret[2] /= ret[3]
        return ret
