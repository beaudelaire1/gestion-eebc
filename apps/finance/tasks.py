"""
Tâches Celery pour le module Finance.

Ce module contient les tâches asynchrones pour :
- Traitement OCR des justificatifs
- Génération de rapports
- Notifications financières
"""

import logging
from celery import shared_task
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_ocr_task(self, receipt_proof_id):
    """
    Tâche Celery pour traiter l'OCR d'un justificatif.
    
    Args:
        receipt_proof_id (int): ID du ReceiptProof à traiter
    
    Returns:
        dict: Résultat du traitement OCR
    
    Requirements: 17.1
    """
    from .models import ReceiptProof
    from .ocr_service import ocr_service
    
    try:
        # Récupérer le justificatif
        receipt_proof = ReceiptProof.objects.get(id=receipt_proof_id)
        
        logger.info(f"Starting OCR processing for receipt {receipt_proof_id}")
        
        # Marquer comme en cours
        receipt_proof.ocr_status = ReceiptProof.OCRStatus.EN_COURS
        receipt_proof.save()
        
        # Traiter avec OCR
        result = ocr_service.process_receipt(receipt_proof)
        
        if 'error' in result:
            # Marquer comme échec
            receipt_proof.ocr_status = ReceiptProof.OCRStatus.ECHEC
            receipt_proof.save()
            
            logger.error(f"OCR failed for receipt {receipt_proof_id}: {result['error']}")
            
            # Retry si c'est une erreur temporaire
            if self.request.retries < self.max_retries:
                logger.info(f"Retrying OCR for receipt {receipt_proof_id} (attempt {self.request.retries + 1})")
                raise self.retry(countdown=60 * (self.request.retries + 1))
            
            return {
                'success': False,
                'error': result['error'],
                'receipt_id': receipt_proof_id
            }
        
        # Succès
        receipt_proof.ocr_status = ReceiptProof.OCRStatus.TERMINE
        receipt_proof.ocr_processed_at = timezone.now()
        receipt_proof.save()
        
        logger.info(f"OCR completed successfully for receipt {receipt_proof_id}")
        
        # Notifier l'utilisateur qui a uploadé le justificatif
        if receipt_proof.uploaded_by and receipt_proof.uploaded_by.email:
            try:
                send_ocr_completion_notification.delay(
                    receipt_proof_id=receipt_proof_id,
                    user_email=receipt_proof.uploaded_by.email,
                    success=True,
                    extracted_amount=str(result.get('amount', 'N/A')),
                    extracted_date=str(result.get('date', 'N/A'))
                )
            except Exception as e:
                logger.warning(f"Failed to send OCR completion notification: {e}")
        
        return {
            'success': True,
            'receipt_id': receipt_proof_id,
            'extracted_amount': result.get('amount'),
            'extracted_date': result.get('date'),
            'confidence': result.get('confidence'),
            'raw_text_length': len(result.get('text', ''))
        }
        
    except ReceiptProof.DoesNotExist:
        logger.error(f"Receipt proof {receipt_proof_id} not found")
        return {
            'success': False,
            'error': 'Receipt proof not found',
            'receipt_id': receipt_proof_id
        }
        
    except Exception as exc:
        logger.error(f"Unexpected error in OCR processing for receipt {receipt_proof_id}: {exc}")
        
        # Marquer comme échec
        try:
            receipt_proof = ReceiptProof.objects.get(id=receipt_proof_id)
            receipt_proof.ocr_status = ReceiptProof.OCRStatus.ECHEC
            receipt_proof.save()
        except:
            pass
        
        # Retry si possible
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying OCR for receipt {receipt_proof_id} due to unexpected error")
            raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))
        
        return {
            'success': False,
            'error': str(exc),
            'receipt_id': receipt_proof_id
        }


@shared_task
def send_ocr_completion_notification(receipt_proof_id, user_email, success, extracted_amount=None, extracted_date=None):
    """
    Envoie une notification de fin de traitement OCR.
    
    Args:
        receipt_proof_id (int): ID du justificatif traité
        user_email (str): Email de l'utilisateur à notifier
        success (bool): Succès ou échec du traitement
        extracted_amount (str): Montant extrait (si succès)
        extracted_date (str): Date extraite (si succès)
    
    Requirements: 17.3
    """
    try:
        from .models import ReceiptProof
        
        receipt_proof = ReceiptProof.objects.get(id=receipt_proof_id)
        transaction_ref = receipt_proof.transaction.reference if receipt_proof.transaction else 'N/A'
        
        if success:
            subject = f"OCR terminé - Justificatif {receipt_proof_id}"
            message = f"""Le traitement OCR de votre justificatif est terminé.

Transaction: {transaction_ref}
Justificatif ID: {receipt_proof_id}

Données extraites:
- Montant: {extracted_amount}€
- Date: {extracted_date}

Vous pouvez maintenant consulter les résultats dans l'interface de gestion des finances.

Cordialement,
L'équipe EEBC"""
        else:
            subject = f"OCR échoué - Justificatif {receipt_proof_id}"
            message = f"""Le traitement OCR de votre justificatif a échoué.

Transaction: {transaction_ref}
Justificatif ID: {receipt_proof_id}

Vous pouvez relancer le traitement manuellement depuis l'interface de gestion des finances.

Cordialement,
L'équipe EEBC"""
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user_email],
            fail_silently=False
        )
        
        logger.info(f"OCR notification sent to {user_email} for receipt {receipt_proof_id}")
        
    except Exception as e:
        logger.error(f"Failed to send OCR notification: {e}")


@shared_task
def batch_process_ocr(receipt_proof_ids):
    """
    Traite plusieurs justificatifs OCR en lot.
    
    Args:
        receipt_proof_ids (list): Liste des IDs de justificatifs à traiter
    
    Returns:
        dict: Résumé du traitement en lot
    """
    results = {
        'total': len(receipt_proof_ids),
        'success': 0,
        'failed': 0,
        'errors': []
    }
    
    for receipt_id in receipt_proof_ids:
        try:
            # Lancer la tâche OCR pour chaque justificatif
            result = process_ocr_task.delay(receipt_id)
            
            # Attendre le résultat (avec timeout)
            task_result = result.get(timeout=300)  # 5 minutes max par justificatif
            
            if task_result.get('success'):
                results['success'] += 1
            else:
                results['failed'] += 1
                results['errors'].append({
                    'receipt_id': receipt_id,
                    'error': task_result.get('error', 'Unknown error')
                })
                
        except Exception as e:
            results['failed'] += 1
            results['errors'].append({
                'receipt_id': receipt_id,
                'error': str(e)
            })
    
    logger.info(f"Batch OCR processing completed: {results['success']} success, {results['failed']} failed")
    
    return results


@shared_task
def cleanup_failed_ocr_tasks():
    """
    Nettoie les justificatifs avec statut OCR "en_cours" depuis plus de 1 heure.
    Tâche de maintenance à exécuter périodiquement.
    """
    from .models import ReceiptProof
    from datetime import timedelta
    
    cutoff_time = timezone.now() - timedelta(hours=1)
    
    # Trouver les justificatifs bloqués en "en_cours"
    # Utiliser uploaded_at car updated_at n'existe pas sur ce modèle
    stuck_receipts = ReceiptProof.objects.filter(
        ocr_status=ReceiptProof.OCRStatus.EN_COURS,
        uploaded_at__lt=cutoff_time
    )
    
    count = stuck_receipts.count()
    
    if count > 0:
        # Marquer comme échec
        stuck_receipts.update(ocr_status=ReceiptProof.OCRStatus.ECHEC)
        logger.warning(f"Cleaned up {count} stuck OCR tasks")
    
    return {
        'cleaned_up': count,
        'cutoff_time': cutoff_time.isoformat()
    }


@shared_task
def generate_ocr_statistics():
    """
    Génère des statistiques sur l'utilisation de l'OCR.
    
    Returns:
        dict: Statistiques OCR
    """
    from .models import ReceiptProof
    from django.db.models import Count, Avg, Q
    
    stats = ReceiptProof.objects.aggregate(
        total_receipts=Count('id'),
        processed_receipts=Count('id', filter=Q(ocr_status=ReceiptProof.OCRStatus.TERMINE)),
        failed_receipts=Count('id', filter=Q(ocr_status=ReceiptProof.OCRStatus.ECHEC)),
        pending_receipts=Count('id', filter=Q(ocr_status=ReceiptProof.OCRStatus.NON_TRAITE)),
        processing_receipts=Count('id', filter=Q(ocr_status=ReceiptProof.OCRStatus.EN_COURS)),
        avg_confidence=Avg('ocr_confidence')
    )
    
    # Calculer les pourcentages
    total = stats['total_receipts'] or 1
    stats['success_rate'] = (stats['processed_receipts'] / total) * 100
    stats['failure_rate'] = (stats['failed_receipts'] / total) * 100
    
    logger.info(f"OCR Statistics: {stats}")
    
    return stats