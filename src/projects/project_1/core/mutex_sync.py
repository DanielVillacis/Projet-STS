"""
Implémentation de la synchronisation par mutex pour la gestion des accès concurrents.
"""
import threading 
import time
import random

class MutexSyncManager:
    def __init__(self, seed=None, monitor=None, perf_monitor=None):
        self.mutex = threading.Lock()
        self.card_locks = {} # verrous pour les cartes
        self.card_balances = {} # soldes pour les cartes
        self.stop_locks = {} # verrous pour les arrêts de bus
        self.seed = seed
        self.monitor = monitor
        self.perf_monitor = perf_monitor
        self.threads = []
        self.stop_signal = False


    # Complétez la méthode initialize() pour créer les mutex et initialiser les soldes des
    # cartes.
    def initialize(self):
        """
        Initialise les mutex et les soldes des cartes.
        
        Returns:
            bool: True si l'initialisation a réussi, False sinon
        """
        try:
            # Récupérer les IDs des cartes et des arrêts depuis seed
            if self.seed:
                # Les passengers sont stockés dans un dictionnaire avec l'ID comme clé
                passenger_ids = list(self.seed.passengers.keys())
                # Les stops sont stockés dans un dictionnaire avec le nom comme clé
                stop_ids = [stop_name for stop_name in self.seed.stops.keys()]
            else:
                # Si pas de seed, utiliser des valeurs par défaut pour les tests
                passenger_ids = [i for i in range(10)]
                stop_ids = [f"S{i}" for i in range(10)]
            
            # Initialiser les cartes
            for card_id in passenger_ids:
                self.card_locks[card_id] = threading.Lock()
                self.card_balances[card_id] = random.uniform(10.0, 100.0)
                
            # Initialiser les arrêts
            for stop_id in stop_ids:
                self.stop_locks[stop_id] = threading.Lock()
            
            # Indiquer que l'initialisation a réussi
            return True
            
        except Exception as e:
            print(f"Erreur lors de l'initialisation: {e}")
            return False

    
    def pay_fare(self, passenger_id, amount=3.50) -> bool:
        """
        Eﬀectue le paiement du trajet. 
        Args: 
        passenger_id: Identifiant du passager 
        amount: Montant à payer (défaut: 3.50$) 
        Returns: bool: True si le paiement a réussi, False sinon
        """
        if passenger_id not in self.card_locks:
            return False
        
        start_time = time.time()
        success = False

        with self.card_locks[passenger_id]:
            wait_time = time.time() - start_time

            if self.card_balances[passenger_id] >= amount:
                self.card_balances[passenger_id] -= amount
                success = True

            processing_time = time.time() - start_time - wait_time

            if self.perf_monitor:
                self.perf_monitor.record_event('mutex', success, wait_time, processing_time)

        return success
            

    def recharge_card(self, passenger_id, amount) -> bool:
        """ 
        Recharge la carte de transport. 
        Args: 
        passenger_id: Identifiant du passager
        amount: Montant à ajouter
        Returns : bool: True si la recharge a reussi, False sinon
        Attention à l'ajout du montant -> le montant doit toujours etre positif sinon on enlève de l'argent (cas limite)
        """
        start_time = time.time()
        success = False

        if passenger_id not in self.card_locks:
            return False

        if amount <= 0:
            return False

        with self.card_locks[passenger_id]:
            wait_time = time.time() - start_time

            self.card_balances[passenger_id] += amount
            success = True

            processing_time = time.time() - start_time - wait_time

            if self.perf_monitor:
                self.perf_monitor.record_event('mutex', success, wait_time, processing_time)

            return success
    

    def refund(self, passenger_id, amount) -> bool:
        """
        Effectue le remboursement sur la carte.
        Args: 
        passenger_id: Identifiant du passager
        amount: Montant à rembourser
        Returns: bool: True si le remboursement a réussi, False sinon
        Attention a l'ajout du montant a rembourser -> le montant doit toujours etre positif sinon on enleve de l'argent (cas limite)
        """
        start_time = time.time()
        success = False

        if passenger_id not in self.card_locks:
            return False

        if amount <= 0:
            return False

        with self.card_locks[passenger_id]:
            wait_time = time.time() - start_time

            self.card_balances[passenger_id] += amount
            success = True

            processing_time = time.time() - start_time - wait_time

            if self.perf_monitor:
                self.perf_monitor.record_event('mutex', success, wait_time, processing_time)
            return success
        
    
    def buy_monthly(self, passenger_id) -> bool:
        """
        Effectue l'achat d'un pass mensuel.
        Args: passenger_id: Identifiant du passager
        Returns: bool: True si l'achat a réussi, False sinon
        La passe mensuelle coûte 45$.
        """
        start_time = time.time()
        success = False

        if passenger_id not in self.card_locks:
            return False

        with self.card_locks[passenger_id]:
            wait_time = time.time() - start_time

            self.card_balances[passenger_id] -= 45
            success = True

            processing_time = time.time() - start_time - wait_time

            if self.perf_monitor:
                self.perf_monitor.record_event('mutex', success, wait_time, processing_time)
            
            return success
        
    
    # implementarion des montées/descentes
    def board_passengers(self, stop, bus, worker_id=None) -> bool:
        """
        Gere la montée des passagers d'un bus a un arret.
        Args:
        stop: l'arret ou a lieu la montée de bus.
        bus: le bus concerné
        worker_id: identifiant optionnel du worker.
        Returns: bool : True si la montée des passagers a réussi, False sinon
        Si un passager monte dans le bus, il doit payer le trajet de 3.50$. Ce montant devrait etre deduit de son solde.
        """
        if stop not in self.stop_locks:
            return False
        
        start_time = time.time()
    
        with self.stop_locks[stop]:
            wait_time = time.time() - start_time

            # Vérifier si le bus peut accepter tous les passagers
            if not bus.can_accept_passengers(len(stop.passenger_list)):
                if self.perf_monitor: # on enregistrer le fail de l'opération
                    self.perf_monitor.record_event('bus', False, wait_time, 0.0)
                return False
            
            # copie de la liste des passagers pour éviter les modifications concurrentes
            passengers_to_board = list(stop.passenger_list)
            boarded = False
            
            for passenger in passengers_to_board:
                if self.pay_fare(passenger.id): # au moins un passager a reussi a payer
                    bus.passenger_list.append(passenger)
                    stop.passenger_list.remove(passenger)
                    boarded = True

            processing_time = time.time() - start_time - wait_time

            # on enregistre la performance de l'opération
            if self.perf_monitor:
                self.perf_monitor.record_event('bus', boarded, wait_time, processing_time)
                self.perf_monitor.record_event('stop', boarded, wait_time, processing_time) 
            
            return boarded 
        
    
    def alight_passengers(self, stop, bus, worker_id=None) -> bool:
        """
        Gere la descente des passagers d'un bus a un arret.
        Args:
        Stop: l'arret ou a lieu la descente de bus.
        worker_id: identifiant optionnel du worker.
        Returns: bool : True si la descente des passagers a réussi, False sinon
        """
        if stop not in self.stop_locks:
            return False
        
        start_time = time.time()
        
        with self.stop_locks[stop]:
            wait_time = time.time() - start_time

            # Vérifier si l'arrêt peut accepter tous les passagers
            if not stop.can_accept_passengers(len(bus.passenger_list)):
                if self.perf_monitor: # on enregistrer le fail de l'opération
                    self.perf_monitor.record_event('stop', False, wait_time, 0.0)
                return False
            
            # Faire une copie de la liste des passagers pour éviter les modifications concurrentes
            passengers_to_alight = list(bus.passenger_list)
            removed = False
            
            for passenger in passengers_to_alight:
                # on enleve le passager du bus et on l'ajoute a l'arret
                bus.passenger_list.remove(passenger)
                stop.passenger_list.append(passenger)
                removed = True

            processing_time = time.time() - start_time - wait_time

            # on enregistre la performance de l'opération
            if self.perf_monitor:
                self.perf_monitor.record_event('bus', removed, wait_time, processing_time)
                self.perf_monitor.record_event('stop', removed, wait_time, processing_time)

            return removed
        

    def run_scenarios(self, duration):
        """
        Execute les scenarios de test.
        Args: duration: Duree d'execution des scenarios en secondes.
        """
        # a- reinitialisation du signal d'arret
        self.stop_signal = False

        def scenario_1():
            while not self.stop_signal:
                # payer un trajet et recharger une carte
                for card_id in self.card_locks.keys():
                    self.pay_fare(card_id)
                    self.recharge_card(card_id, 10)
                time.sleep(0.5)

        def scenario_2():
            while not self.stop_signal:
                # acheter une passe mensuelle
                for card_id in self.card_locks.keys():
                    self.buy_monthly(card_id)
                time.sleep(0.5)

        # b- creation des threads pour les scenarios
        t1 = threading.Thread(target=scenario_1, name="Scenario de Thread 1")
        t2 = threading.Thread(target=scenario_2, name="Scenario de Thread 2")

        self.threads = [t1, t2]

        # c- demarrage des threads
        for t in self.threads:
            t.start()

        # d- attente pendant la duree specifiee
        time.sleep(duration)

        # e- arret des threads
        self.stop_signal = True

        # f- attente de la fin des threads
        for t in self.threads:
            t.join()

        print("Scenarios des Threads terminés")
        
                
    def cleanup(self):
        """ Nettoie les ressources utilisees. """
        # Arrêter les threads s'ils sont en cours d'exécution
        self.stop_signal = True
        for thread in self.threads:
            if thread.is_alive():
                thread.join()
        
        # Vider les dictionnaires sans essayer de libérer les verrous
        # qui pourraient ne pas être actuellement verrouillés
        self.card_locks.clear()
        self.card_balances.clear()
        self.stop_locks.clear()
        
        print("Ressources nettoyées")
        
    

        
            
    