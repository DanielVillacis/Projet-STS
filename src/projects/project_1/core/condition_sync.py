"""
Implémentation de la synchronisation par variables de condition.

Gère:
- Coordination entre bus et passagers
- Synchronisation des départs de bus
- Gestion des correspondances

Utilise des variables de condition pour:
- Signaler les arrivées/départs des bus
- Coordonner les montées/descentes des passagers
- Gérer les attentes de correspondance
"""
import threading
import time

class ConditionSyncManager:
    def __init__(self, seed=None, monitor=None, perf_monitor=None):
        # Variables de configuration
        self.seed = seed
        self.monitor = monitor
        self.perf_monitor = perf_monitor
        # Variables de condition
        self.stop_conditions = {}
        self.bus_conditions = {} # Conditions pour les bus
        self.transfer_condition = None # Condition globale pour les correspondances
        # États partagés à protéger
        self.bus_at_stop = {} # Stocke les bus présents à chaque arrêt
        self.boarding_complete = {} # État d'embarquement pour chaque bus
        self.alighting_complete = {} # État de débarquement 
        self.transfers_in_progress = {} # Transferts en cours


    def initialize(self) -> bool:
        """ 
        Initialise les variables de condition et les états partagés. 
        Returns: bool: True si l'initialisation a réussi, False sinon 
        Initialisation des conditions pour les arrêts
        Initialisation des conditions pour les bus
        Initialisation de la condition globale pour les correspondances
        """
        try:
            # creation d'un lock global pour les conditions de transfert
            self.transfer_condition = threading.Condition(threading.RLock())

            # recuperation des donnees du seed s'il existe
            if self.seed:
                bus_ids = list(self.seed.buses.keys())
                stop_ids = list(self.seed.stops.keys())
            
            # initialisation des conditions pour les arrets
            for stop_id in stop_ids:
                self.stop_conditions[stop_id] = threading.Condition(threading.RLock())
                self.bus_at_stop[stop_id] = set() # un set vide des bus a cet arret, j'utilise le set pour eviter les doublons

            # initialisation des conditions pour les bus
            for bus_id in bus_ids:
                self.bus_conditions[bus_id] = threading.Condition(threading.RLock())
                self.boarding_complete[bus_id] = False
                self.alighting_complete[bus_id] = False

            # initialisation des conditions pour les bus
            for bus_id in bus_ids:
                self.bus_conditions[bus_id] = threading.Condition(threading.RLock())
                self.boarding_complete[bus_id] = False
                self.alighting_complete[bus_id] = False

            self.stop_signal = False

            return True

        except Exception as e:
            print(f"Erreur lors de l'initialisation: {e}")
            return False
        
    def wait_for_bus(self, passenger_id, stop_id, target_bus_id=None, timeout=30.0) -> int:
        """ 
        Un passager attend qu'un bus spécifique (ou n'importe quel bus) arrive à un arrêt.
        Args: 
        passenger_id: Identifiant du passager 
        stop_id: Identifiant de l'arrêt 
        target_bus_id: Identifiant du bus spécifique attendu (None pour n'importe quel bus) 
        timeout: Délai d'attente maximum en secondes 
        Returns: int: L'identifiant du bus arrivé, ou -1 si timeout
        """
        if stop_id not in self.stop_conditions:
            return -1
        
        start_time = time.time()
        bus_found = None # pour stocker le resultat

        start_time = time.time()
        with self.stop_conditions[stop_id]:

            acquire_time = time.time() - start_time
            wait_start_time = time.time()

            while True:
                if self.stop_signal:
                    bus_found = -1
                    break
                
                if target_bus_id:
                    if target_bus_id in self.bus_at_stop[stop_id]:
                        bus_found = target_bus_id
                        break
                else:
                    if self.bus_at_stop[stop_id]:
                        bus_found = next(iter(self.bus_at_stop[stop_id]))
                        break
                    
                elapsed_time = time.time() - start_time
                if elapsed_time >= timeout:
                    bus_found = -1
                    break
                self.stop_conditions[stop_id].wait(timeout - elapsed_time)
        
        #calculer les temps pour les metriques de performance
        total_time = time.time() - start_time
        wait_time = time.time() - wait_start_time
        processing_time = total_time - wait_time
        success = (bus_found != -1)

        # enregistrer les metriques de performance
        if self.perf_monitor:
            metadata = {"passenger_id" : passenger_id}
            self.perf_monitor.record_event('condition', success, wait_time, processing_time, metadata=metadata)
            self.perf_monitor.record_event('passenger', success, wait_time, processing_time)

        return bus_found if bus_found is not None else -1


    def notify_bus_arrival(self, bus_id, stop_id) -> bool:
        """
        Notifie tous les passagers en attente qu'un bus est arrivé à un arrêt. 
        Args: bus_id: Identifiant du bus 
        stop_id: Identifiant de l'arrêt 
        Returns: bool: True si la notification a réussi, False sinon
        """
        start_time = time.time()

        if stop_id not in self.stop_conditions:
            if self.perf_monitor:
                processing_time = time.time() - start_time
                self.perf_monitor.record_event('condition', False, 0.0, processing_time)
                self.perf_monitor.record_event('bus', False, 0.0, processing_time)
            return False
        
        pre_lock_time = time.time()

        with self.stop_conditions[stop_id]:
            wait_time = time.time() - pre_lock_time

            self.bus_at_stop[stop_id].add(bus_id)
            self.stop_conditions[stop_id].notify_all()

            processing_time = time.time() - start_time

            if self.perf_monitor:
                metadata = {"bus_id" : bus_id, "stop_id" : stop_id}
                self.perf_monitor.record_event('condition', True, wait_time, processing_time, metadata=metadata)
                self.perf_monitor.record_event('bus', True, wait_time, processing_time)
                self.perf_monitor.record_event('stop', True, wait_time, processing_time)
        
            return True

    def notify_bus_departure(self, bus_id, stop_id) -> bool:
        """ 
        Notifie que le bus quitte l'arrêt et met à jour l'état. 
        Args: bus_id: Identifiant du bus
        stop_id: Identifiant de l'arrêt 
        Returns: bool: True si la notification a réussi, False sinon 
        """
        start_time = time.time()

        if stop_id not in self.stop_conditions:
            if self.perf_monitor:
                processing_time = time.time() - start_time
                self.perf_monitor.record_event('condition', False, 0.0, processing_time)
                self.perf_monitor.record_event('bus', False, 0.0, processing_time)
            return False
        
        pre_lock_time = time.time()

        with self.stop_conditions[stop_id]:
            wait_time = time.time() - pre_lock_time

            self.bus_at_stop[stop_id].discard(bus_id)
            self.stop_conditions[stop_id].notify_all()

            processing_time = time.time() - pre_lock_time - wait_time

            if self.perf_monitor:
                metadata = {"bus_id" : bus_id, "stop_id" : stop_id}
                self.perf_monitor.record_event('condition', True, wait_time, processing_time, metadata=metadata)
                self.perf_monitor.record_event('bus', True, wait_time, processing_time)
                self.perf_monitor.record_event('stop', True, wait_time, processing_time)
        
            return True

    def start_boarding(self, bus_id, stop_id) -> bool:
        """ 
        Commence l'opération d'embarquement des passagers dans un bus. 
        Args: bus_id: Identifiant du bus 
        stop_id: Identifiant de l'arrêt 
        Returns: bool: True si l'opération a commencé avec succès, False sinon 
        """
        start_time = time.time()

        if bus_id not in self.bus_conditions:
            return False

        pre_lock_time = time.time()

        with self.bus_conditions[bus_id]:
            wait_time = time.time() - pre_lock_time

            if self.boarding_complete[bus_id]:
                return False

            self.boarding_complete[bus_id] = False
            self.bus_conditions[bus_id].notify_all()

            processing_time = time.time() - pre_lock_time - wait_time

            if self.perf_monitor:
                metadata = {"bus_id" : bus_id, "stop_id" : stop_id}
                self.perf_monitor.record_event('condition', True, 0.0, processing_time, metadata=metadata)
                self.perf_monitor.record_event('bus', True, 0.0, processing_time)
        
            return True
        

    def complete_boarding(self, bus_id) -> bool:
        """ 
        Marque l'opération d'embarquement comme terminée et notifie le bus. 
        Args: bus_id: Identifiant du bus 
        Returns: bool: True si la notification a réussi, False sinon 
        """
        # Vérifier que le bus existe
        if bus_id not in self.bus_conditions:
            return False
        
        pre_lock_time = time.time()
        
        with self.bus_conditions[bus_id]:
            wait_time = time.time() - pre_lock_time
            
            # Mettre à jour l'état d'embarquement
            self.boarding_complete[bus_id] = True
            
            # Notifier tous les threads en attente (notamment le bus)
            self.bus_conditions[bus_id].notify_all()
            
            processing_time = time.time() - pre_lock_time - wait_time
            
            # Enregistrer les métriques de performance
            if self.perf_monitor:
                metadata = {"bus_id": bus_id}
                self.perf_monitor.record_event('condition', True, wait_time, processing_time, metadata=metadata)
                self.perf_monitor.record_event('bus', True, wait_time, processing_time)
            
            return True


    def wait_for_boarding_completion(self, bus_id, timeout=10.0) -> bool:
        """ 
        Le bus attend que l'embarquement des passagers soit terminé. 
        Args: bus_id: Identifiant du bus 
        timeout: Délai d'attente maximum en secondes 
        Returns: bool: True si l'embarquement est terminé, False si timeout 
        """
        start_time = time.time()
    
        # Vérifier que le bus existe
        if bus_id not in self.bus_conditions:
            return False

        pre_lock_time = time.time()
    
        with self.bus_conditions[bus_id]:
            wait_time = time.time() - pre_lock_time
            
            # Calculer le temps restant pour le timeout
            elapsed = time.time() - start_time
            remaining_timeout = max(0, timeout - elapsed)
            
            # Attendre que l'embarquement soit marqué comme terminé ou que le timeout expire
            while not self.boarding_complete[bus_id] and remaining_timeout > 0:
                # Wait retourne False si le timeout expire, True si la condition est notifiée
                wait_result = self.bus_conditions[bus_id].wait(remaining_timeout)
                
                # Recalculer le temps restant
                elapsed = time.time() - start_time
                remaining_timeout = max(0, timeout - elapsed)
                
                # Si le signal d'arrêt est activé ou si le timeout a expiré, sortir
                if self.stop_signal or not wait_result:
                    break
            
            # Déterminer si l'embarquement est terminé
            is_complete = self.boarding_complete[bus_id]
            
            # Calculer les métriques de performance
            processing_time = time.time() - pre_lock_time - wait_time
            
            # Enregistrer les métriques
            if self.perf_monitor:
                metadata = {"bus_id": bus_id}
                self.perf_monitor.record_event('condition', is_complete, wait_time, processing_time, metadata=metadata)
                self.perf_monitor.record_event('bus', is_complete, wait_time, processing_time)
            
            return is_complete


    def start_alighting(self, bus_id, stop_id) -> bool:
        """ 
        Commence l'opération de débarquement des passagers d'un bus. 
        Args: bus_id: Identifiant du bus 
        stop_id: Identifiant de l'arrêt 
        Returns: bool: True si l'opération a commencé avec succès, False sinon 
        """
        # Vérifier que le bus existe
        if bus_id not in self.bus_conditions:
            return False

        pre_lock_time = time.time()

        with self.bus_conditions[bus_id]:
            wait_time = time.time() - pre_lock_time

            # Si le débarquement est déjà en cours, ne pas le redémarrer
            if not self.alighting_complete[bus_id]:
                return False

            # Marquer le débarquement comme en cours (non terminé)
            self.alighting_complete[bus_id] = False
            
            # Notifier tous les threads en attente (les passagers)
            self.bus_conditions[bus_id].notify_all()

            processing_time = time.time() - pre_lock_time - wait_time

            if self.perf_monitor:
                metadata = {"bus_id": bus_id, "stop_id": stop_id}
                self.perf_monitor.record_event('condition', True, wait_time, processing_time, metadata=metadata)
                self.perf_monitor.record_event('bus', True, wait_time, processing_time)
                
            print(f"Débarquement commencé pour le bus {bus_id} à l'arrêt {stop_id}")
        
            return True


    def complete_alighting(self, bus_id) -> bool:
        """ 
        Marque l'opération de débarquement comme terminée et notifie le bus. 
        Args: bus_id: Identifiant du bus 
        Returns: bool: True si la notification a réussi, False sinon 
        """
        # Vérifier que le bus existe
        if bus_id not in self.bus_conditions:
            return False
        
        pre_lock_time = time.time()
        
        with self.bus_conditions[bus_id]:
            wait_time = time.time() - pre_lock_time
            
            # Mettre à jour l'état de débarquement
            self.alighting_complete[bus_id] = True
            
            # Notifier tous les threads en attente (notamment le bus)
            self.bus_conditions[bus_id].notify_all()
            
            processing_time = time.time() - pre_lock_time - wait_time
            
            # Enregistrer les métriques de performance
            if self.perf_monitor:
                metadata = {"bus_id": bus_id}
                self.perf_monitor.record_event('condition', True, wait_time, processing_time, metadata=metadata)
                self.perf_monitor.record_event('bus', True, wait_time, processing_time)
            
            print(f"Débarquement terminé pour le bus {bus_id}")
            
            return True

    def wait_for_alighting_completion(self, bus_id, timeout=10.0) -> bool:
        """ 
        Le bus a:end que le débarquement des passagers soit terminé. 
        Args: bus_id: Identifiant du bus 
        timeout: Délai d'attente maximum en secondes 
        Returns: bool: True si le débarquement est terminé, False si timeout 
        """
        start_time = time.time()
    
        # Vérifier que le bus existe
        if bus_id not in self.bus_conditions:
            return False
        
        pre_lock_time = time.time()
        
        with self.bus_conditions[bus_id]:
            wait_time = time.time() - pre_lock_time
            
            # Calculer le temps restant pour le timeout
            elapsed = time.time() - start_time
            remaining_timeout = max(0, timeout - elapsed)
            
            # Attendre que le débarquement soit marqué comme terminé ou que le timeout expire
            while not self.alighting_complete[bus_id] and remaining_timeout > 0:
                # Wait retourne False si le timeout expire, True si la condition est notifiée
                wait_result = self.bus_conditions[bus_id].wait(remaining_timeout)
                
                # Recalculer le temps restant
                elapsed = time.time() - start_time
                remaining_timeout = max(0, timeout - elapsed)
                
                # Si le signal d'arrêt est activé ou si le timeout a expiré, sortir
                if self.stop_signal or not wait_result:
                    break
            
            # Déterminer si le débarquement est terminé
            is_complete = self.alighting_complete[bus_id]
            
            # Calculer les métriques de performance
            processing_time = time.time() - pre_lock_time - wait_time
            
            # Enregistrer les métriques
            if self.perf_monitor:
                metadata = {"bus_id": bus_id}
                self.perf_monitor.record_event('condition', is_complete, wait_time, processing_time, metadata=metadata)
                self.perf_monitor.record_event('bus', is_complete, wait_time, processing_time)
            
            print(f"Bus {bus_id}: {'Débarquement terminé' if is_complete else 'Timeout de débarquement'}")
            
            return is_complete


    def start_transfer(self, passenger_id, from_bus_id, to_bus_id) -> bool:
        """ 
        Commence un transfert de passager entre deux bus. 
        Args: passenger_id: Identifiant du passager f
        rom_bus_id: Bus de départ 
        to_bus_id: Bus d'arrivée 
        Returns: bool: True si le transfert a commencé avec succès, False sinon 
        """
        # Vérifier que les bus existent
        if from_bus_id not in self.bus_conditions or to_bus_id not in self.bus_conditions:
            return False
        
        pre_lock_time = time.time()
        
        with self.transfer_condition:
            wait_time = time.time() - pre_lock_time
            
            # Vérifier si un transfert est déjà en cours pour ce passager
            if passenger_id in self.transfers_in_progress:
                return False
            
            # Ajouter le transfert en cours
            self.transfers_in_progress[passenger_id] = (from_bus_id, to_bus_id)
            
            # Notifier tous les threads en attente (les bus)
            self.transfer_condition.notify_all()
            
            processing_time = time.time() - pre_lock_time - wait_time
            
            # Enregistrer les métriques de performance
            if self.perf_monitor:
                metadata = {"passenger_id": passenger_id, "from_bus_id": from_bus_id, "to_bus_id": to_bus_id}
                self.perf_monitor.record_event('condition', True, wait_time, processing_time, metadata=metadata)
                self.perf_monitor.record_event('passenger', True, wait_time, processing_time)
            
            print(f"Transfert commencé pour le passager {passenger_id} de {from_bus_id} à {to_bus_id}")
        
            return True
        


    def complete_transfer(self, passenger_id, from_bus_id, to_bus_id) -> bool:
        """ 
        Termine un transfert de passager et notifie les bus concernés. 
        Args: passenger_id: Identifiant du passager 
        from_bus_id: Bus de départ 
        to_bus_id: Bus d'arrivée 
        Returns: bool: True si le transfert a été terminé avec succès, False sinon 
        """
        # Vérifier que les bus existent
        if from_bus_id not in self.bus_conditions or to_bus_id not in self.bus_conditions:
            return False
        
        pre_lock_time = time.time()
        
        with self.transfer_condition:
            wait_time = time.time() - pre_lock_time
            
            # Vérifier si le transfert est en cours pour ce passager
            if passenger_id not in self.transfers_in_progress:
                return False
            
            # Vérifier que le transfert est correct
            if self.transfers_in_progress[passenger_id] != (from_bus_id, to_bus_id):
                return False
            
            # Supprimer le transfert en cours
            del self.transfers_in_progress[passenger_id]
            
            # Notifier tous les threads en attente (les bus)
            self.transfer_condition.notify_all()
            
            processing_time = time.time() - pre_lock_time - wait_time
            
            # Enregistrer les métriques de performance
            if self.perf_monitor:
                metadata = {"passenger_id": passenger_id, "from_bus_id": from_bus_id, "to_bus_id": to_bus_id}
                self.perf_monitor.record_event('condition', True, wait_time, processing_time, metadata=metadata)
                self.perf_monitor.record_event('passenger', True, wait_time, processing_time)
            
            print(f"Transfert terminé pour le passager {passenger_id} de {from_bus_id} à {to_bus_id}")
        
            return True



    def wait_for_transfer_completion(self, bus_id, timeout=15.0) -> bool:
        """ 
        Un bus attend que tous les transferts le concernant soient terminés. 
        Args: bus_id: Identifiant du bus 
        timeout: Délai d'attente maximum en secondes 
        Returns: bool: True si tous les transferts sont terminés, False si timeout """
        start_time = time.time()
    
        # Vérifier que le bus existe
        if bus_id not in self.bus_conditions:
            if self.perf_monitor:
                processing_time = time.time() - start_time
                self.perf_monitor.record_event('condition', False, 0.0, processing_time)
                self.perf_monitor.record_event('bus', False, 0.0, processing_time)
            return False
            
        pre_lock_time = time.time()
        
        with self.transfer_condition:
            wait_time = time.time() - pre_lock_time
            
            # Calculer le délai restant
            elapsed = time.time() - start_time
            remaining_timeout = max(0, timeout - elapsed)
            
            # Fonction pour vérifier si des transferts concernent ce bus
            def has_pending_transfers():
                for passenger_id, (from_bus, to_bus) in self.transfers_in_progress.items():
                    if from_bus == bus_id or to_bus == bus_id:
                        return True
                return False
            
            # Attendre tant qu'il y a des transferts en cours pour ce bus
            while has_pending_transfers() and remaining_timeout > 0:
                # Attendre avec le timeout restant
                wait_result = self.transfer_condition.wait(remaining_timeout)
                
                # Recalculer le temps restant
                elapsed = time.time() - start_time
                remaining_timeout = max(0, timeout - elapsed)
                
                # Si le signal d'arrêt est activé, sortir
                if self.stop_signal or not wait_result:
                    break
            
            # Vérifier si tous les transferts sont terminés
            transfers_completed = not has_pending_transfers()
            
            # Calculer les métriques de performance
            processing_time = time.time() - pre_lock_time - wait_time
            
            # Enregistrer les métriques
            if self.perf_monitor:
                metadata = {"bus_id": bus_id}
                self.perf_monitor.record_event('condition', transfers_completed, wait_time, processing_time, metadata=metadata)
                self.perf_monitor.record_event('bus', transfers_completed, wait_time, processing_time)
            
            print(f"Bus {bus_id}: {'Tous les transferts sont terminés' if transfers_completed else 'Timeout sur attente des transferts'}")
            
            return transfers_completed
            

        

    def run_scenarios(self, duration):
        """ 
        Exécute les scénarios de test. 
        Args: duration: Durée d'exécution des scénarios en secondes 
        """
        

    def cleanup(self):
        """ 
        Nettoie les ressources utilisées par le gestionnaire de synchronisation. 
        """

