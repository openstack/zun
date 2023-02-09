from zun.common import exception

class K8sException(exception.ZunException):
    message = "Failed to perform operation on K8s"

class ReservationException(exception.Invalid):
    message = "Received invalid or missing reservation_id"
