from django.db import models
class PredictionLog(models.Model):
    """Digital-twin history: every prediction / what-if run is stored here."""
    employee_id = models.CharField(max_length=50, blank=True)
    kind = models.CharField(max_length=20)          # predict | whatif
    model_name = models.CharField(max_length=50)
    inputs = models.JSONField()
    label = models.CharField(max_length=50)
    confidence = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ["-created_at"]
