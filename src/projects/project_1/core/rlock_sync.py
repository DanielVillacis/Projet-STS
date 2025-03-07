"""Implémentation de la synchronisation par RLock pour la gestion des réservations et transferts"""
class RLockSyncManager:
    def __init__(self):
        self.reservation_locks = {}  # RLocks pour les réservations
        self.transfer_locks = {}  # RLocks pour les transferts
        self.reservations = {}  # Réservations de cartes
        self

