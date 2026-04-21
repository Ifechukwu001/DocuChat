from .document import document_queue, queue_document_for_processing
from .dead_letter import dead_letter_queue

__all__ = ["dead_letter_queue", "document_queue", "queue_document_for_processing"]
