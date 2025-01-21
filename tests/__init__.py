import threading 
import time
from src.projects.project_1.core.mutex_sync import MutexSyncManager, BusStop

def test_concurrent_transactions():
    card = MutexSyncManager()

    def transaction_recharge():
        card.paiement_trajet()
        card.recharge(10.0)
        card.achat_passe_mensuel()

    def transaction_remboursement():
        card.recharge(20)
        card.paiement_trajet()
        card.remboursement(5)

    t1 = threading.Thread(target=transaction_recharge)
    t2 = threading.Thread(target=transaction_remboursement)

    t1.start()
    t2.start()

    t1.join()
    t2.join()

    print(f"Solde final: {card.balance}$")
    assert card.balance >= 0.0, "Le solde ne doit pas être négatif"