"""
Implémentation de la synchronisation par sémaphores.

Gère:
- La capacité des bus (nombre maximum de passagers)
- Le nombre maximum de bus aux arrêts

Utilise des sémaphores pour garantir:
- Qu'un bus ne dépasse jamais sa capacité
- Qu'un arrêt ne dépasse pas sa limite de bus
"""
import threading
import time

class SemaphoreSyncManager:
    def __init__(self, seed=None, monitor=None, perf_monitor=None):
        self.bus_capacity_semaphores = {}
        self.stop_semaphores = {}
        self.stop_queues = {}
        self.stop_locks = {}
        self.seed = seed
        self.monitor = monitor
        self.perf_monitor = perf_monitor

    
    def initialize(self) -> bool:
        """
        Initialise les semaphores pour les bus et les arrets.
        Returns -> bool: True si l'initialisation a réussi, False sinon
        """
        try:
            if self.seed:
                # recuperer les bus depuis le seed
                if hasattr(self.seed, 'buses'):
                    buses = self.seed.buses
                else:
                    print("Seed does not have buses")
                    return False
                
                # recuperer les arrets depuis le seed
                if hasattr(self.seed, 'stops'):
                    stops = self.seed.stops
                else:
                    print("Seed does not have stops")
                    return False
            else:
                # on cree des donnees de test
                buses = {f"Bus{i}" : {"id": f"Bus{i}", "capacity": 50} for i in range(1, 6)}
                stops = {f"Stop{i}" : {"id": f"Stop{i}"} for i in range(1, 6)}

            
            # initialisation des semaphores pour le bus basé sur sa capacite
            for bus_id, bus_data in buses.items():
                # Utiliser la notation d'attribut si c'est un objet Bus, sinon la notation de dictionnaire
                if hasattr(bus_data, 'capacity'):
                    capacity = bus_data.capacity
                else:
                    capacity = bus_data["capacity"]
                self.bus_capacity_semaphores[bus_id] = threading.Semaphore(capacity)


            # initialisation des semaphores pour les stops
            for stop_id in stops:
                # creer un semaphore avec un compteur de 2 (max 2 bus par arret selon l'ennoncé)
                self.stop_semaphores[stop_id] = threading.Semaphore(2)
                # initialisation de la file d'attente pour l'arret
                self.stop_queues[stop_id] = []
                # creation d'un lock pour proteger la file d'attente
                self.stop_locks[stop_id] = threading.Lock()

            return True
        
        except Exception as e:
            print(f"Erreur d'initialisation des semaphores: {e}")
            return False


    def board_passenger(self, bus_id, passenger_id, timeout=2.0) -> bool:
        """
        Fait monter un passager dans un bus si la capacité le permet
        Args:
        bus_id: Identifiant du bus 
        passenger_id: Identifiant du passager 
        timeout: Délai d'attente maximum en secondes 
        Returns: bool: True si le passager a pu monter, False sinon
        """
        start_time = time.time()
        success = False

        try:
            # on verifie que le bus existe
            if bus_id not in self.bus_capacity_semaphores:
                print(f"Bus {bus_id} not found")
                return False
            
            # on recupere le semaphore du bus avec un timeout pour eviter les blocages
            if self.bus_capacity_semaphores[bus_id].acquire(timeout=timeout):
                wait_time = time.time() - start_time

                # # on met a jour l'etat du passager
                # if self.monitor:
                #     self.monitor.update_passenger_state(passenger_id, "onboarded", bus_id)
                #     self.monitor.update_bus_state(bus_id, "passenger_boarded", passenger_id)

                success = True
                processing_time = time.time() - start_time - wait_time

                # Enregistrement de la performance
                if self.perf_monitor:
                    self.perf_monitor.record_event('semaphore', success, wait_time, processing_time)
                    self.perf_monitor.record_event('bus', success, wait_time, processing_time)
                    self.perf_monitor.record_event('passenger', success, wait_time, processing_time)
                
                return True
            
            else:
                # le timeout a expire
                print(f"Timeout: Le passager {passenger_id} n'a pas pu monter dans le bus {bus_id}")

                return False
            
        except Exception as e:
            print(f"Erreur lors de la montée du passager: {e}")
            return False
        

    def alight_passenger(self, bus_id, passenger_id) -> bool:
        """ 
        Fait descendre un passager d'un bus. 
        Args: bus_id: Identifiant du bus 
        passenger_id: Identifiant du passager 
        Returns: bool: True si le passager a pu descendre, False sinon 
        """
        start_time = time.time()
        success = False

        try:
            # on verifie que le bus existe
            if bus_id not in self.bus_capacity_semaphores:
                print(f"Bus {bus_id} not found")
                return False

            # Libérer une place dans le bus en relâchant le sémaphore
            self.bus_capacity_semaphores[bus_id].release()
            
            wait_time = time.time() - start_time
            
            success = True
            processing_time = time.time() - start_time - wait_time
            
            # Enregistrement des métriques de performance
            if self.perf_monitor:
                self.perf_monitor.record_event('semaphore', success, wait_time, processing_time)
                self.perf_monitor.record_event('bus', success, wait_time, processing_time)
                self.perf_monitor.record_event('passenger', success, wait_time, processing_time)
            
            return success
            
        except Exception as e:
            print(f"Erreur lors de la descente du passager: {e}")
            return False
        

    def bus_arrive_at_stop(self, bus_id, stop_id, timeout=5.0) -> bool:
        """ 
        Gère l'arrivée d'un bus à un arrêt. 
        Args: bus_id: Identifiant du bus 
        stop_id: Identifiant de l'arrêt 
        timeout: Délai d'attente maximum en secondes 
        Returns: bool: True si le bus a pu accéder à l'arrêt, False sinon 
        """
        start_time = time.time()
        
        # verifier que l'arret existe
        if stop_id not in self.stop_semaphores:
            print(f"Stop {stop_id} not found")
            return False
        
        # ajouter le bus a la file d'attente de l'arret
        with self.stop_locks[stop_id]:
            self.stop_queues[stop_id].append(bus_id)

        try:
            # attente FIFO avec timeout
            end_time = start_time + timeout
            while time.time() < end_time:
                with self.stop_locks[stop_id]:
                    # si ce bus n'est pas en tete de file, on continue d'attendre
                    if not self.stop_queues[stop_id] or self.stop_queues[stop_id][0] != bus_id:
                        time.sleep(0.1)
                        continue

                    # on recupere le semaphore de l'arret
                    if self.stop_semaphores[stop_id].acquire(blocking=False):
                        # on reture le bus de la file d'attente
                        self.stop_queues[stop_id].pop(0)
                        wait_time = time.time() - start_time

                        # enregistrer les performances:
                        if self.perf_monitor:
                            processing_time = time.time() - start_time - wait_time
                            self.perf_monitor.record_event('semaphore', True, wait_time, processing_time)
                            self.perf_monitor.record_event('stop', True, wait_time, processing_time)

                        return True
                time.sleep(0.1)

            # timeout: on retire le bus de la file d'attente
            with self.stop_locks[stop_id]:
                if bus_id in self.stop_queues[stop_id]:
                    self.stop_queues[stop_id].remove(bus_id)
            return False
        
        except Exception as e:
            print(f"Erreur lors de l'arrivee du bus a l'arret: {e}")
            # nettoyer la file d'attente
            with self.stop_locks[stop_id]:
                if bus_id in self.stop_queues[stop_id]:
                    self.stop_queues[stop_id].remove(bus_id)
            return False
        

    def bus_depart_from_stop(self, bus_id, stop_id) -> bool:
        """ 
        Gère le départ d'un bus d'un arrêt. 
        Args: bus_id: Identifiant du bus 
        stop_id: Identifiant de l'arrêt 
        Returns: bool: True si le bus a pu quitter l'arrêt, False sinon
        4.7. Vérification que le bus est bien à cet arrêt
        4.8. Mise à jour de l'état du bus et de l'arrêt
        4.9. Retrait du bus de la liste des bus de l'arrêt
        """
        start_time = time.time()

        try:
            # verifier que l'arret existe
            if stop_id not in self.stop_semaphores:
                print(f"arret {stop_id} non trouvée")
                return False

            # on libere le semaphore pour permettre à un autre bus d'accéder à l'arrêt
            self.stop_semaphores[stop_id].release()

            wait_time = time.time() - start_time

            processing_time = time.time() - start_time - wait_time
            if self.perf_monitor:
                self.perf_monitor.record_event('semaphore', True, wait_time, processing_time)
                self.perf_monitor.record_event('bus', True, wait_time, processing_time)
                self.perf_monitor.record_event('stop', True, wait_time, processing_time)

            return True
        
        except Exception as e:
            print(f"Erreur lors du depart du bus de l'arret: {e}")
            return False
        

    def run_scenarios(self, duration):
        """ 
        Exécute les scénarios de test. 
        Args: duration: Durée d'exécution des scénarios en secondes 
        5.1. Création des threads pour les scénarios
        5.2. Démarrage des threads
        5.3. Attente de la fin des threads
        """
        # Variable pour indiquer aux threads quand s'arrêter
        self.stop_signal = False
        self.threads = []
    
        # Scénario 1: Simulation de montée/descente de passagers
        def passenger_scenario():
            bus_ids = list(self.bus_capacity_semaphores.keys())
            if not bus_ids:
                print("Aucun bus disponible pour le scénario passager")
                return
                
            passenger_count = 100  # Nombre de passagers à simuler
            
            while not self.stop_signal:
                for i in range(passenger_count):
                    passenger_id = f"P{i}"
                    bus_id = bus_ids[i % len(bus_ids)]
                    
                    # Essayer de faire monter un passager
                    if self.board_passenger(bus_id, passenger_id):
                        print(f"Passager {passenger_id} est monté dans le bus {bus_id}")
                        
                        # Attendre un peu avant de faire descendre le passager
                        time.sleep(0.5)
                        
                        # Faire descendre le passager
                        if self.alight_passenger(bus_id, passenger_id):
                            print(f"Passager {passenger_id} est descendu du bus {bus_id}")
                    
                    # Pause courte entre les opérations
                    time.sleep(0.1)
                    
                    if self.stop_signal:
                        break
        
        # Scénario 2: Simulation de bus arrivant/partant des arrêts
        def bus_stop_scenario():
            bus_ids = list(self.bus_capacity_semaphores.keys())
            stop_ids = list(self.stop_semaphores.keys())
            
            if not bus_ids or not stop_ids:
                print("Aucun bus ou arrêt disponible pour le scénario d'arrêt")
                return
                
            while not self.stop_signal:
                for i, bus_id in enumerate(bus_ids):
                    # Choisir un arrêt pour ce bus
                    stop_id = stop_ids[i % len(stop_ids)]
                    
                    # Essayer de faire arriver le bus à l'arrêt
                    if self.bus_arrive_at_stop(bus_id, stop_id):
                        print(f"Bus {bus_id} est arrivé à l'arrêt {stop_id}")
                        
                        # Attendre un peu à l'arrêt
                        time.sleep(1.0)
                        
                        # Faire partir le bus de l'arrêt
                        if self.bus_depart_from_stop(bus_id, stop_id):
                            print(f"Bus {bus_id} a quitté l'arrêt {stop_id}")
                    
                    # Pause courte entre les opérations
                    time.sleep(0.2)
                    
                    if self.stop_signal:
                        break
        
        # Scénario 3: Test de contention aux arrêts (plusieurs bus essayant d'accéder au même arrêt)
        def bus_contention_scenario():
            bus_ids = list(self.bus_capacity_semaphores.keys())
            
            if not bus_ids or len(self.stop_semaphores) == 0:
                print("Aucun bus ou arrêt disponible pour le scénario de contention")
                return
                
            # Choisir un arrêt pour tester la contention
            test_stop = list(self.stop_semaphores.keys())[0]
            
            while not self.stop_signal:
                for bus_id in bus_ids:
                    # Tous les bus essaient d'accéder au même arrêt
                    if self.bus_arrive_at_stop(bus_id, test_stop, timeout=1.0):
                        print(f"Bus {bus_id} a réussi à accéder à l'arrêt {test_stop}")
                        
                        # Attendre un peu avant de partir
                        time.sleep(0.5)
                        
                        self.bus_depart_from_stop(bus_id, test_stop)
                    else:
                        print(f"Bus {bus_id} n'a pas pu accéder à l'arrêt {test_stop} (occupé)")
                    
                    time.sleep(0.1)
                    
                    if self.stop_signal:
                        break
        
        # 5.1. Création des threads pour les scénarios
        t1 = threading.Thread(target=passenger_scenario, name="PassengerScenario")
        t2 = threading.Thread(target=bus_stop_scenario, name="BusStopScenario")
        t3 = threading.Thread(target=bus_contention_scenario, name="BusContentionScenario")
        
        self.threads = [t1, t2, t3]
        
        # 5.2. Démarrage des threads
        for thread in self.threads:
            thread.start()
        
        # Attente pendant la durée spécifiée
        time.sleep(duration)
        
        # Arrêt des threads
        self.stop_signal = True
        
        # 5.3. Attente de la fin des threads
        for thread in self.threads:
            thread.join()
            
        print("Scénarios des threads terminés")

    def cleanup(self):
        """ Nettoie les ressources utilisees """
        # arret des threads en cours d'execution
        self.stop_signal = True

        # attendre la fin des threads
        for thread in self.threads:
            if thread.is_alive():
                thread.join(timeout=2.0) # attendre 2 secondes max

        # reinitialiser les threads
        self.threads = []

        # reinitialiser les semaphores
        self.bus_capacity_semaphores = {}
        self.stop_semaphores = {}
        self.stop_queues = {}
        self.stop_locks = {}

        # reinitialiser le signal d'arret
        self.stop_signal = False

        print("Ressources de semaphore nettoyées")