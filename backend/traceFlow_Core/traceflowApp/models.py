from django.db import models

class Trace(models.Model):
    trace_id = models.CharField(max_length=32, db_index=True)
    span_id = models.CharField(max_length=16, db_index=True)
    parent_span_id = models.CharField(max_length=16, null=True, blank=True)
    data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    # client_ip = models.CharField(max_length=45, null=True, blank=True, db_index=True)

    class Meta:
        db_table = 'traces'
        indexes = [
            models.Index(fields=['trace_id', 'created_at']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"Trace {self.trace_id} - Span {self.span_id}"
    
class Example(models.Model):
    example = models.CharField(max_length=16, db_index=True)


