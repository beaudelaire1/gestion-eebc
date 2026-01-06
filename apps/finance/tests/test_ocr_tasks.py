"""
Tests pour les tâches Celery OCR.

Property 10: Celery Task Execution
Validates: Requirements 17.1, 17.2, 17.3, 17.4
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from hypothesis import given, strategies as st, settings
from hypothesis.extra.django import TestCase as HypothesisTestCase

from apps.finance.models import FinancialTransaction, ReceiptProof
from apps.finance.tasks import (
    process_ocr_task, 
    send_ocr_completion_notification,
    batch_process_ocr,
    cleanup_failed_ocr_tasks,
    generate_ocr_statistics
)

User = get_user_model()


class OCRTasksTestCase(TestCase):
    """Tests unitaires pour les tâches OCR."""
    
    def setUp(self):
        """Configuration des tests."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role='finance'
        )
        
        self.transaction = FinancialTransaction.objects.create(
            amount=Decimal('100.00'),
            transaction_type='depense',
            transaction_date=date.today(),
            recorded_by=self.user
        )
        
        # Créer un fichier image factice
        self.image_file = SimpleUploadedFile(
            "test_receipt.jpg",
            b"fake image content",
            content_type="image/jpeg"
        )
        
        self.receipt_proof = ReceiptProof.objects.create(
            transaction=self.transaction,
            image=self.image_file,
            uploaded_by=self.user,
            ocr_status=ReceiptProof.OCRStatus.NON_TRAITE
        )
    
    def test_process_ocr_task_success(self):
        """Test du traitement OCR réussi."""
        # Mock du service OCR
        mock_result = {
            'text': 'Facture test montant 100.00€ date 2024-01-15',
            'amount': Decimal('100.00'),
            'date': date(2024, 1, 15),
            'confidence': 85.5
        }
        
        # Mock de l'OCR service pour qu'il ne mette pas à jour le modèle
        def mock_process_receipt(receipt_proof):
            # Simuler la mise à jour du modèle comme le ferait le vrai service
            receipt_proof.ocr_status = ReceiptProof.OCRStatus.TERMINE
            receipt_proof.ocr_raw_text = mock_result['text']
            receipt_proof.ocr_extracted_amount = mock_result['amount']
            receipt_proof.ocr_extracted_date = mock_result['date']
            receipt_proof.ocr_confidence = mock_result['confidence']
            receipt_proof.ocr_processed_at = timezone.now()
            receipt_proof.save()
            return mock_result
        
        with patch('apps.finance.ocr_service.ocr_service.process_receipt', side_effect=mock_process_receipt):
            # Exécuter la tâche
            result = process_ocr_task(self.receipt_proof.id)
            
            # Vérifications
            self.assertTrue(result['success'])
            self.assertEqual(result['receipt_id'], self.receipt_proof.id)
            self.assertEqual(result['extracted_amount'], Decimal('100.00'))
            self.assertEqual(result['confidence'], 85.5)
            
            # Vérifier que le modèle a été mis à jour
            self.receipt_proof.refresh_from_db()
            self.assertEqual(self.receipt_proof.ocr_status, ReceiptProof.OCRStatus.TERMINE)
            self.assertEqual(self.receipt_proof.ocr_extracted_amount, Decimal('100.00'))
            self.assertEqual(self.receipt_proof.ocr_extracted_date, date(2024, 1, 15))
            self.assertEqual(self.receipt_proof.ocr_confidence, 85.5)
            self.assertIsNotNone(self.receipt_proof.ocr_processed_at)
    
    def test_process_ocr_task_failure(self):
        """Test du traitement OCR en échec."""
        # Mock du service OCR qui échoue
        def mock_process_receipt_failure(receipt_proof):
            # Simuler l'échec comme le ferait le vrai service
            receipt_proof.ocr_status = ReceiptProof.OCRStatus.ECHEC
            receipt_proof.save()
            return {'error': 'Tesseract not available'}
        
        # Mock de la tâche pour désactiver les retries
        with patch('apps.finance.ocr_service.ocr_service.process_receipt', side_effect=mock_process_receipt_failure), \
             patch.object(process_ocr_task, 'max_retries', 0):
            
            # Exécuter la tâche
            result = process_ocr_task(self.receipt_proof.id)
            
            # Vérifications
            self.assertFalse(result['success'])
            self.assertEqual(result['error'], 'Tesseract not available')
            self.assertEqual(result['receipt_id'], self.receipt_proof.id)
            
            # Vérifier que le modèle a été mis à jour
            self.receipt_proof.refresh_from_db()
            self.assertEqual(self.receipt_proof.ocr_status, ReceiptProof.OCRStatus.ECHEC)
    
    def test_process_ocr_task_receipt_not_found(self):
        """Test avec un justificatif inexistant."""
        result = process_ocr_task(99999)
        
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'Receipt proof not found')
        self.assertEqual(result['receipt_id'], 99999)
    
    @patch('apps.finance.tasks.send_mail')
    def test_send_ocr_completion_notification_success(self, mock_send_mail):
        """Test de notification de succès OCR."""
        send_ocr_completion_notification(
            receipt_proof_id=self.receipt_proof.id,
            user_email='test@example.com',
            success=True,
            extracted_amount='100.00',
            extracted_date='2024-01-15'
        )
        
        # Vérifier que l'email a été envoyé
        mock_send_mail.assert_called_once()
        args, kwargs = mock_send_mail.call_args
        
        self.assertIn('OCR terminé', kwargs['subject'])
        self.assertIn('100.00€', kwargs['message'])
        self.assertIn('2024-01-15', kwargs['message'])
        self.assertEqual(kwargs['recipient_list'], ['test@example.com'])
    
    @patch('apps.finance.tasks.send_mail')
    def test_send_ocr_completion_notification_failure(self, mock_send_mail):
        """Test de notification d'échec OCR."""
        send_ocr_completion_notification(
            receipt_proof_id=self.receipt_proof.id,
            user_email='test@example.com',
            success=False
        )
        
        # Vérifier que l'email a été envoyé
        mock_send_mail.assert_called_once()
        args, kwargs = mock_send_mail.call_args
        
        self.assertIn('OCR échoué', kwargs['subject'])
        self.assertIn('relancer le traitement', kwargs['message'])
    
    def test_cleanup_failed_ocr_tasks(self):
        """Test du nettoyage des tâches OCR bloquées."""
        # Créer un justificatif bloqué en "en_cours" depuis plus d'1 heure
        old_time = timezone.now() - timedelta(hours=2)
        
        stuck_receipt = ReceiptProof.objects.create(
            transaction=self.transaction,
            image=self.image_file,
            uploaded_by=self.user,
            ocr_status=ReceiptProof.OCRStatus.EN_COURS
        )
        
        # Simuler une ancienne date de mise à jour en utilisant uploaded_at
        ReceiptProof.objects.filter(id=stuck_receipt.id).update(uploaded_at=old_time)
        
        # Exécuter le nettoyage
        result = cleanup_failed_ocr_tasks()
        
        # Vérifications
        self.assertEqual(result['cleaned_up'], 1)
        
        stuck_receipt.refresh_from_db()
        self.assertEqual(stuck_receipt.ocr_status, ReceiptProof.OCRStatus.ECHEC)
    
    def test_generate_ocr_statistics(self):
        """Test de génération des statistiques OCR."""
        # Créer différents justificatifs avec différents statuts
        ReceiptProof.objects.create(
            transaction=self.transaction,
            image=self.image_file,
            uploaded_by=self.user,
            ocr_status=ReceiptProof.OCRStatus.TERMINE,
            ocr_confidence=90.0
        )
        
        ReceiptProof.objects.create(
            transaction=self.transaction,
            image=self.image_file,
            uploaded_by=self.user,
            ocr_status=ReceiptProof.OCRStatus.ECHEC
        )
        
        # Exécuter la génération de statistiques
        stats = generate_ocr_statistics()
        
        # Vérifications
        self.assertEqual(stats['total_receipts'], 3)  # 1 du setUp + 2 créés ici
        self.assertEqual(stats['processed_receipts'], 1)
        self.assertEqual(stats['failed_receipts'], 1)
        self.assertEqual(stats['pending_receipts'], 1)
        self.assertEqual(stats['avg_confidence'], 90.0)
        self.assertAlmostEqual(stats['success_rate'], 33.33, places=1)
        self.assertAlmostEqual(stats['failure_rate'], 33.33, places=1)


class OCRTasksPropertyTestCase(HypothesisTestCase):
    """Tests basés sur les propriétés pour les tâches OCR."""
    
    def setUp(self):
        """Configuration des tests."""
        # Utiliser un nom d'utilisateur unique pour éviter les conflits
        import uuid
        username = f'testuser_{uuid.uuid4().hex[:8]}'
        
        self.user = User.objects.create_user(
            username=username,
            email=f'{username}@example.com',
            password='testpass123',
            role='finance'
        )
    
    @given(
        amount=st.decimals(min_value=1, max_value=10000, places=2),
        confidence=st.floats(min_value=0.0, max_value=100.0)
    )
    @settings(max_examples=50, deadline=5000)
    def test_property_ocr_task_execution(self, amount, confidence):
        """
        Property 10: Celery Task Execution
        
        Pour tout justificatif valide, si une tâche OCR est créée,
        alors le statut du justificatif doit être trackable jusqu'à
        completion ou échec.
        
        Validates: Requirements 17.1, 17.2, 17.3, 17.4
        """
        # Créer une transaction et un justificatif
        transaction = FinancialTransaction.objects.create(
            amount=amount,
            transaction_type='depense',
            transaction_date=date.today(),
            recorded_by=self.user
        )
        
        image_file = SimpleUploadedFile(
            "test_receipt.jpg",
            b"fake image content",
            content_type="image/jpeg"
        )
        
        receipt_proof = ReceiptProof.objects.create(
            transaction=transaction,
            image=image_file,
            uploaded_by=self.user,
            ocr_status=ReceiptProof.OCRStatus.NON_TRAITE
        )
        
        # Mock du service OCR avec résultat réussi
        mock_result = {
            'text': f'Facture test montant {amount}€',
            'amount': amount,
            'date': date.today(),
            'confidence': confidence
        }
        
        # Mock de l'OCR service
        def mock_process_receipt(receipt_proof):
            # Simuler la mise à jour du modèle comme le ferait le vrai service
            receipt_proof.ocr_status = ReceiptProof.OCRStatus.TERMINE
            receipt_proof.ocr_raw_text = mock_result['text']
            receipt_proof.ocr_extracted_amount = mock_result['amount']
            receipt_proof.ocr_extracted_date = mock_result['date']
            receipt_proof.ocr_confidence = mock_result['confidence']
            receipt_proof.ocr_processed_at = timezone.now()
            receipt_proof.save()
            return mock_result
        
        # Mock de l'OCR service
        def mock_process_receipt(receipt_proof):
            # Simuler la mise à jour du modèle comme le ferait le vrai service
            receipt_proof.ocr_status = ReceiptProof.OCRStatus.TERMINE
            receipt_proof.ocr_raw_text = mock_result['text']
            receipt_proof.ocr_extracted_amount = mock_result['amount']
            receipt_proof.ocr_extracted_date = mock_result['date']
            receipt_proof.ocr_confidence = mock_result['confidence']
            receipt_proof.ocr_processed_at = timezone.now()
            receipt_proof.save()
            return mock_result
        
        with patch('apps.finance.ocr_service.ocr_service.process_receipt', side_effect=mock_process_receipt):
            
            # Exécuter la tâche OCR
            result = process_ocr_task(receipt_proof.id)
            
            # Propriété: La tâche doit toujours retourner un résultat trackable
            self.assertIsInstance(result, dict)
            self.assertIn('success', result)
            self.assertIn('receipt_id', result)
            self.assertEqual(result['receipt_id'], receipt_proof.id)
            
            # Si succès, les données extraites doivent être cohérentes
            if result['success']:
                self.assertEqual(result['extracted_amount'], amount)
                self.assertEqual(result['confidence'], confidence)
                
                # Le modèle doit refléter le succès
                receipt_proof.refresh_from_db()
                self.assertEqual(receipt_proof.ocr_status, ReceiptProof.OCRStatus.TERMINE)
                self.assertEqual(receipt_proof.ocr_extracted_amount, amount)
                self.assertEqual(receipt_proof.ocr_confidence, confidence)
                self.assertIsNotNone(receipt_proof.ocr_processed_at)
    
    @given(
        receipt_count=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=20, deadline=10000)
    def test_property_batch_ocr_processing(self, receipt_count):
        """
        Property: Traitement en lot OCR
        
        Pour tout lot de justificatifs, le traitement en lot doit
        traiter chaque justificatif individuellement et retourner
        un résumé cohérent.
        
        Validates: Requirements 17.1, 17.4
        """
        # Créer plusieurs justificatifs
        receipt_ids = []
        
        for i in range(receipt_count):
            transaction = FinancialTransaction.objects.create(
                amount=Decimal('100.00'),
                transaction_type='depense',
                transaction_date=date.today(),
                recorded_by=self.user
            )
            
            image_file = SimpleUploadedFile(
                f"test_receipt_{i}.jpg",
                b"fake image content",
                content_type="image/jpeg"
            )
            
            receipt_proof = ReceiptProof.objects.create(
                transaction=transaction,
                image=image_file,
                uploaded_by=self.user,
                ocr_status=ReceiptProof.OCRStatus.NON_TRAITE
            )
            
            receipt_ids.append(receipt_proof.id)
        
        # Mock du traitement OCR (alternance succès/échec)
        def mock_process_ocr(receipt_id):
            # Simuler succès pour les IDs pairs, échec pour les impairs
            if receipt_id % 2 == 0:
                return {
                    'success': True,
                    'receipt_id': receipt_id,
                    'extracted_amount': Decimal('100.00'),
                    'confidence': 85.0
                }
            else:
                return {
                    'success': False,
                    'receipt_id': receipt_id,
                    'error': 'Simulated OCR failure'
                }
        
        with patch('apps.finance.tasks.process_ocr_task.delay') as mock_task:
            # Configurer le mock pour retourner des résultats
            mock_task.side_effect = lambda rid: Mock(get=lambda timeout=None: mock_process_ocr(rid))
            
            # Exécuter le traitement en lot
            result = batch_process_ocr(receipt_ids)
            
            # Propriétés du traitement en lot
            self.assertEqual(result['total'], receipt_count)
            self.assertEqual(result['success'] + result['failed'], receipt_count)
            self.assertIsInstance(result['errors'], list)
            
            # Vérifier que chaque justificatif a été traité
            self.assertEqual(mock_task.call_count, receipt_count)
    
    @given(
        hours_old=st.integers(min_value=2, max_value=24)
    )
    @settings(max_examples=10, deadline=5000)
    def test_property_cleanup_stuck_tasks(self, hours_old):
        """
        Property: Nettoyage des tâches bloquées
        
        Pour toute tâche OCR bloquée depuis plus d'1 heure,
        elle doit être marquée comme échec lors du nettoyage.
        
        Validates: Requirements 17.1, 17.4
        """
        # Créer un justificatif bloqué
        transaction = FinancialTransaction.objects.create(
            amount=Decimal('100.00'),
            transaction_type='depense',
            transaction_date=date.today(),
            recorded_by=self.user
        )
        
        image_file = SimpleUploadedFile(
            "stuck_receipt.jpg",
            b"fake image content",
            content_type="image/jpeg"
        )
        
        stuck_receipt = ReceiptProof.objects.create(
            transaction=transaction,
            image=image_file,
            uploaded_by=self.user,
            ocr_status=ReceiptProof.OCRStatus.EN_COURS
        )
        
        # Simuler une ancienne date de mise à jour en utilisant uploaded_at
        old_time = timezone.now() - timedelta(hours=hours_old)
        ReceiptProof.objects.filter(id=stuck_receipt.id).update(uploaded_at=old_time)
        
        # Exécuter le nettoyage
        result = cleanup_failed_ocr_tasks()
        
        # Propriété: Les tâches anciennes doivent être nettoyées
        if hours_old > 1:
            self.assertGreaterEqual(result['cleaned_up'], 1)
            
            stuck_receipt.refresh_from_db()
            self.assertEqual(stuck_receipt.ocr_status, ReceiptProof.OCRStatus.ECHEC)
        else:
            # Si moins d'1 heure, ne devrait pas être nettoyé
            self.assertEqual(result['cleaned_up'], 0)


# Tests d'intégration avec Celery (nécessitent un broker Redis/RabbitMQ)
@pytest.mark.integration
class OCRCeleryIntegrationTestCase(TestCase):
    """Tests d'intégration avec Celery (optionnels)."""
    
    def setUp(self):
        """Configuration des tests d'intégration."""
        import uuid
        username = f'integration_user_{uuid.uuid4().hex[:8]}'
        
        self.user = User.objects.create_user(
            username=username,
            email=f'{username}@example.com',
            password='testpass123',
            role='finance'
        )
    
    @pytest.mark.skipif(
        not hasattr(pytest, 'celery_app'),
        reason="Celery broker not available"
    )
    def test_celery_task_execution_integration(self):
        """Test d'intégration avec un vrai broker Celery."""
        # Ce test nécessite un broker Celery configuré
        transaction = FinancialTransaction.objects.create(
            amount=Decimal('100.00'),
            transaction_type='depense',
            transaction_date=date.today(),
            recorded_by=self.user
        )
        
        image_file = SimpleUploadedFile(
            "integration_test.jpg",
            b"fake image content",
            content_type="image/jpeg"
        )
        
        receipt_proof = ReceiptProof.objects.create(
            transaction=transaction,
            image=image_file,
            uploaded_by=self.user,
            ocr_status=ReceiptProof.OCRStatus.NON_TRAITE
        )
        
        # Lancer la tâche réelle
        from apps.finance.tasks import process_ocr_task
        
        # Mock de l'OCR service
        def mock_process_receipt(receipt_proof):
            # Simuler la mise à jour du modèle comme le ferait le vrai service
            receipt_proof.ocr_status = ReceiptProof.OCRStatus.TERMINE
            receipt_proof.ocr_raw_text = mock_result['text']
            receipt_proof.ocr_extracted_amount = mock_result['amount']
            receipt_proof.ocr_extracted_date = mock_result['date']
            receipt_proof.ocr_confidence = mock_result['confidence']
            receipt_proof.ocr_processed_at = timezone.now()
            receipt_proof.save()
            return mock_result
        
        with patch('apps.finance.ocr_service.ocr_service.process_receipt', side_effect=mock_process_receipt):
            mock_ocr.return_value = {
                'text': 'Test receipt',
                'amount': Decimal('100.00'),
                'date': date.today(),
                'confidence': 85.0
            }
            
            # Exécuter la tâche de manière synchrone pour les tests
            result = process_ocr_task.apply(args=[receipt_proof.id])
            
            # Vérifier le résultat
            self.assertTrue(result.successful())
            task_result = result.result
            self.assertTrue(task_result['success'])
            
            # Vérifier que le modèle a été mis à jour
            receipt_proof.refresh_from_db()
            self.assertEqual(receipt_proof.ocr_status, ReceiptProof.OCRStatus.TERMINE)


# Configuration pour les tests avec Hypothesis
def load_tests(loader, tests, ignore):
    """Configuration personnalisée pour les tests Hypothesis."""
    # Configurer Hypothesis pour des tests plus rapides en développement
    import os
    
    if os.environ.get('HYPOTHESIS_PROFILE') == 'dev':
        from hypothesis import settings
        settings.register_profile('dev', max_examples=10, deadline=1000)
        settings.load_profile('dev')
    
    return tests