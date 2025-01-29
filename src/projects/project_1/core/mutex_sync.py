"""
Implémentation de la synchronisation par mutex pour la gestion des accès concurrents.
"""
import threading 

class MutexSyncManager:
    def __init__(self):
        self.mutex = threading.Lock()
        self.balance = 0.0

    def paiement_trajet(self):
        with self.mutex:
            if self.balance >= 3.5:
                self.balance -= 3.5
                print(f"Trajet payé: -3.50$, Solde actuel: {self.balance}$")
            else:
                print(f"Solde insuffisant: {self.balance}$")

    def recharge(self, montant):
        with self.mutex:
            self.balance += montant
            print(f"Recharge de {montant}$ effectuée, Solde actuel: {self.balance}$")

    def remboursement(self, montant):
        with self.mutex:
            self.balance += montant
            print(f"Remboursement de {montant}$ effectué, Solde actuel: {self.balance}$")

    def achat_passe_mensuel(self):
        with self.mutex:
            if self.balance >= 45.0:
                self.balance -= 45.0
                print(f"Passe mensuel acheté: -45.00$, Solde actuel: {self.balance}$")
            else:
                print(f"Solde insuffisant pour acheter la passe mensuel: {self.balance}$")

class BusStop:
    def __init__(self, capacity):
        self.mutex = threading.RLock()
        self.capacity = capacity
        self.passengers = []

    def board_passenger(self, passenger):
        with self.mutex:
            if len(self.passengers) < self.capacity:
                self.passengers.append(passenger)
                print(f"Passager {passenger} embarqué. Passagers actuels: {len(self.passengers)}")
            else:
                print(f"Capacité maximale atteinte. {passenger} refusé")

    def unboard_passenger(self, passenger):
        with self.mutex:
            if passenger in self.passengers:
                self.passengers.remove(passenger)
                print(f"Passager {passenger} descendu. Passagers actuels: {len(self.passengers)}")
            else:
                print(f"Passager {passenger} non trouvé dans le bus.")
