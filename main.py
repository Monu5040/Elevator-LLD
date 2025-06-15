from enum import Enum, auto
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
import heapq

# ========== ENUMS ==========
class Direction(Enum):
    UP = auto()
    DOWN = auto()
    IDLE = auto()

class Status(Enum):
    MOVING = auto()
    STOPPED = auto()
    IDLE = auto()

# ========== OBSERVER PATTERN ==========
class ElevatorObserver(ABC):
    @abstractmethod
    def update(self):
        pass

class ElevatorObservable(ABC):
    def __init__(self):
        self.observers: List[ElevatorObserver] = []

    def attach(self, observer: ElevatorObserver):
        self.observers.append(observer)

    def notify(self):
        for observer in self.observers:
            observer.update()

# ========== STRATEGY PATTERN FOR DISPATCH ==========
class ExternalButtonDispatcherStrategy(ABC):
    @abstractmethod
    def assign_elevator(self, floor: int, direction: Direction):
        pass

class OddDispatcher(ExternalButtonDispatcherStrategy):
    def __init__(self, elevators: Dict[int, 'ElevatorCar']):
        self.elevators = elevators

    def assign_elevator(self, floor: int, direction: Direction):
        if floor % 2 == 1 and 0 in self.elevators:
            self.elevators[0].add_external_request(floor, direction)

class EvenDispatcher(ExternalButtonDispatcherStrategy):
    def __init__(self, elevators: Dict[int, 'ElevatorCar']):
        self.elevators = elevators

    def assign_elevator(self, floor: int, direction: Direction):
        if floor % 2 == 0 and 1 in self.elevators:
            self.elevators[1].add_external_request(floor, direction)

class FixedDispatcher(ExternalButtonDispatcherStrategy):
    def __init__(self, elevators: Dict[int, 'ElevatorCar'], fixed_floors: List[int]):
        self.elevators = elevators
        self.fixed_floors = fixed_floors

    def assign_elevator(self, floor: int, direction: Direction):
        if floor in self.fixed_floors and 2 in self.elevators:
            self.elevators[2].add_external_request(floor, direction)

# ========== MOVEMENT STRATEGY FOR ELEVATOR ==========
class MovementStrategy(ABC):
    @abstractmethod
    def process_requests(self, elevator):
        pass

class LookAlgorithm(MovementStrategy):
    def process_requests(self, elevator):
        requests = set(elevator.internal_requests + list(elevator.external_requests.keys()))

        up_heap = []
        down_heap = []

        for floor in requests:
            if floor > elevator.current_floor:
                heapq.heappush(up_heap, floor)
            elif floor < elevator.current_floor:
                heapq.heappush(down_heap, -floor)
            else:
                elevator.move_to_floor(floor)

        if elevator.direction in [Direction.IDLE, Direction.UP]:
            while up_heap:
                next_floor = heapq.heappop(up_heap)
                elevator.move_to_floor(next_floor)

        if elevator.direction in [Direction.IDLE, Direction.DOWN] or not up_heap:
            while down_heap:
                next_floor = -heapq.heappop(down_heap)
                elevator.move_to_floor(next_floor)

        elevator.status = Status.IDLE
        elevator.direction = Direction.IDLE
        elevator.internal_requests.clear()
        elevator.external_requests.clear()

# ========== OBJECTS ==========
class Display(ElevatorObserver):
    def __init__(self, elevator_id: Optional[int] = None):
        self.elevator_id = elevator_id
        self.current_floor = 0
        self.direction = Direction.IDLE

    def update(self):
        prefix = f"Elevator {self.elevator_id}" if self.elevator_id is not None else "Floor Display"
        print(f"{prefix} - Floor: {self.current_floor}, Direction: {self.direction.name}")

    def show_movement(self, current: int, target: int):
        step = 1 if target > current else -1
        for f in range(current + step, target + step, step):
            prefix = f"Elevator {self.elevator_id}" if self.elevator_id is not None else "Elevator"
            print(f"{prefix} at floor {f}")

class Logger(ElevatorObserver):
    def __init__(self, elevator_id: Optional[int] = None):
        self.elevator_id = elevator_id

    def update(self):
        prefix = f"[Logger] Elevator {self.elevator_id}" if self.elevator_id is not None else "[Logger] Floor"
        print(f"{prefix} updated")

class InternalButton:
    def __init__(self, floor: int):
        self.floor = floor
        self.pressed = False

class ExternalButton:
    def __init__(self, floor: int, direction: Direction):
        self.floor = floor
        self.direction = direction
        self.pressed = False

class Floor:
    def __init__(self, number: int, controller: 'ElevatorController'):
        self.number = number
        self.up_button = ExternalButton(number, Direction.UP)
        self.down_button = ExternalButton(number, Direction.DOWN)
        self.display = Display()
        self.controller = controller

    def press_external_button(self, direction: Direction):
        if direction == Direction.UP:
            self.up_button.pressed = True
        elif direction == Direction.DOWN:
            self.down_button.pressed = True
        self.controller.handle_external_request(self.number, direction)

class ElevatorCar(ElevatorObservable):
    def __init__(self, id: int, strategy: Optional[MovementStrategy] = None):
        super().__init__()
        self.id = id
        self.current_floor = 0
        self.status = Status.IDLE
        self.direction = Direction.IDLE
        self.internal_requests: List[int] = []
        self.external_requests: Dict[int, Direction] = {}
        self.display = Display(elevator_id=id)
        self.logger = Logger(elevator_id=id)
        self.strategy: MovementStrategy = strategy or LookAlgorithm()
        self.attach(self.display)
        self.attach(self.logger)

    def set_movement_strategy(self, strategy: MovementStrategy):
        self.strategy = strategy

    def press_internal_button(self, floor: int):
        if floor not in self.internal_requests:
            self.internal_requests.append(floor)

    def add_external_request(self, floor: int, direction: Direction):
        if floor not in self.external_requests:
            self.external_requests[floor] = direction

    def move_to_floor(self, floor: int):
        self.display.show_movement(self.current_floor, floor)
        self.direction = Direction.UP if floor > self.current_floor else (Direction.DOWN if floor < self.current_floor else Direction.IDLE)
        self.current_floor = floor
        self.status = Status.STOPPED
        self.notify()

    def process_requests(self):
        self.strategy.process_requests(self)

# ========== CONTROLLERS ==========
class ElevatorController:
    def __init__(self, elevators: Dict[int, ElevatorCar], fixed_floors: List[int]):
        self.elevators = elevators
        self.strategies = [
            OddDispatcher(elevators),
            EvenDispatcher(elevators),
            FixedDispatcher(elevators, fixed_floors)
        ]

    def handle_external_request(self, floor: int, direction: Direction):
        for strategy in self.strategies:
            strategy.assign_elevator(floor, direction)

# ========== BUILDING ==========
class Building:
    def __init__(self, num_floors: int, num_elevators: int, fixed_floors: List[int]):
        self.elevators = {i: ElevatorCar(i) for i in range(num_elevators)}
        self.controller = ElevatorController(self.elevators, fixed_floors)
        self.floors = [Floor(i, self.controller) for i in range(num_floors)]

    def process_all_requests(self):
        for elevator in self.elevators.values():
            elevator.process_requests()

# ========== USAGE ==========
if __name__ == "__main__":
    fixed_floors = [0, 5, 9]
    building = Building(num_floors=10, num_elevators=3, fixed_floors=fixed_floors)

    building.floors[3].press_external_button(Direction.UP)  # Odd elevator
    building.floors[4].press_external_button(Direction.UP)  # Even elevator
    building.floors[5].press_external_button(Direction.DOWN)  # Fixed elevator

    building.elevators[0].press_internal_button(7)
    building.elevators[1].press_internal_button(8)
    building.elevators[2].press_internal_button(9)

    building.process_all_requests()
