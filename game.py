from dataclasses import dataclass, field
import sys
import math
import time

MONTHS = 20
DAYS_PER_MONTH = 20

MAX_TUBES_PER_BUILDING = 5
MAX_TELEPORTERS_PER_BUILDING = 1
MAX_PASSENGERS_PER_POD = 10

MODULE_TYPES = 20

SPEED_SCORE = 50
BALANCING_SCORE = 50

# City(
#   resources=2000,
#   tubes={}, 
#   teleporters={}, 
#   pods={}, 
#   landing_pads={
#       0: LandingPod(module_type=0, building_id=0, x=80, y=60, total_astronauts=30, astronauts={1: 15, 2: 15})
#   }, 
#   modules={
#       1: Module(module_type=1, building_id=1, x=40, y=30), 
#       2: Module(module_type=2, building_id=2, x=120, y=30)
#   }, 
#   buildings_by_coords={
#       (80, 60): LandingPod(module_type=0, building_id=0, x=80, y=60, total_astronauts=30, astronauts={1: 15, 2: 15}), 
#       (40, 30): Module(module_type=1, building_id=1, x=40, y=30), 
#       (120, 30): Module(module_type=2, building_id=2, x=120, y=30)
#   }
# ) 

# City(
#     resources=1000, 
#     tubes={
#         (0, 1): Tube(building_1_id=0, building_2_id=1, capacity=1), 
#         (1, 0): Tube(building_1_id=0, building_2_id=1, capacity=1), 
#         (0, 2): Tube(building_1_id=0, building_2_id=2, capacity=1), 
#         (2, 0): Tube(building_1_id=0, building_2_id=2, capacity=1)
#     }, 
#     teleporters={}, 
#     pods={
#         42: Pod(pod_id=42, stops=[0, 1, 0, 2, 0, 1, 0, 2])
#     }, 
#     landing_pads={
#         0: LandingPod(module_type=0, building_id=0, x=80, y=60, total_astronauts=30, astronauts={1: 15, 2: 15})
#     }, 
#     modules={
#         1: Module(module_type=1, building_id=1, x=40, y=30), 
#         2: Module(module_type=2, building_id=2, x=120, y=30)
#     }, 
#     buildings_by_coords={
#         (80, 60): LandingPod(module_type=0, building_id=0, x=80, y=60, total_astronauts=30, astronauts={1: 15, 2: 15}), 
#         (40, 30): Module(module_type=1, building_id=1, x=40, y=30), 
#         (120, 30): Module(module_type=2, building_id=2, x=120, y=30)
#     }
# ) 

def turn(city: "City"):
    debug(city)
    debug("0 -> 1", city.can_build_tube(0, 1))
    debug("0 -> 2", city.can_build_tube(0, 2))
    debug("1 -> 2", city.can_build_tube(1, 2))
    if 3 in city.buildings:
        debug("0 -> 3", city.can_build_tube(0, 3))
        debug("1 -> 3", city.can_build_tube(1, 3))
        debug("2 -> 3", city.can_build_tube(2, 3))

    return "TUBE 0 1;TUBE 0 2;POD 42 0 1 0 2 0 1 0 2"

def dist_sq(x1: int, y1: int, x2: int, y2: int) -> int:
    return (x2 - x1) ** 2 + (y2 - y1) ** 2

def dist(x1: int, y1: int, x2: int, y2: int) -> float:
    return math.sqrt(dist_sq(x1, y1, x2, y2))

def orientation(x1: int, y1: int, x2: int, y2: int, x3: int, y3: int):
    prod = (y3-y1) * (x2-x1) - (y2-y1) * (x3-x1)
    if prod < 0:
        return -1
    if prod > 0:
        return 1
    return 0

def segments_intersect(x1: int, y1: int, x2: int, y2: int, x3: int, y3: int, x4: int, y4: int):
    return orientation(x1, y1, x2, y2, x3, y3) * orientation(x1, y1, x2, y2, x4, y4) < 0 and \
        orientation(x3, y3, x4, y4, x1, y1) * orientation(x3, y3, x4, y4, x2, y2) < 0

def get_tube_cost(x1: int, y1: int, x2: int, y2: int) -> int:
    tube_dist = dist(x1, y1, x2, y2)
    return math.floor(tube_dist / .1)

def debug(*args):
    for arg in args + ("\n",):
        print(arg, end=" ", file=sys.stderr, flush=True)

@dataclass
class Tube:
    building_1_id: int
    building_2_id: int
    capacity: int

@dataclass
class Teleporter:
    building_1_id: int
    building_2_id: int

@dataclass
class Pod:
    pod_id: int
    stops: list[int]

@dataclass
class LandingPod:
    module_type: int
    building_id: int
    x: int
    y: int
    total_astronauts: int
    astronauts: dict[int, int]

@dataclass
class Module:
    module_type: int
    building_id: int
    x: int
    y: int

@dataclass
class City:
    resources: int
    tubes: dict[tuple[int, int], Tube] = field(default_factory=dict)
    teleporters: dict[tuple[int, int], Teleporter] = field(default_factory=dict)
    pods: dict[int, Pod] = field(default_factory=dict)
    landing_pads: dict[int, LandingPod] = field(default_factory=dict)
    modules: dict[int, Module] = field(default_factory=dict)
    buildings: dict[int, LandingPod | Module] = field(default_factory=dict)
    buildings_by_coords: dict[tuple[int, int], LandingPod | Module] = field(default_factory=dict)
    tubes_by_building: dict[int, list[Tube]] = field(default_factory=dict)
    teleporters_by_building: dict[int, list[Teleporter]] = field(default_factory=dict)

    def can_build_tube(self, building_1_id: int, building_2_id: int) -> bool:
        if (building_1_id, building_2_id) in self.tubes:
            # Existing tube
            return False
        
        if building_1_id in self.tubes_by_building and len(self.tubes_by_building[building_1_id]) >= MAX_TUBES_PER_BUILDING:
            # Building 1 has too many tubes
            return False
        
        if building_2_id in self.tubes_by_building and len(self.tubes_by_building[building_2_id]) >= MAX_TUBES_PER_BUILDING:
            # Building 2 has too many tubes
            return False
        
        if building_1_id in self.teleporters_by_building and len(self.teleporters_by_building[building_1_id]) >= MAX_TELEPORTERS_PER_BUILDING:
            # Building 1 already has a teleporter
            return False
        
        if building_2_id in self.teleporters_by_building and len(self.teleporters_by_building[building_2_id]) >= MAX_TELEPORTERS_PER_BUILDING:
            # Building 2 already has a teleporter
            return False

        # Make sure this tube wouldn't intersect another building
        building_1 = self.buildings[building_1_id]
        building_2 = self.buildings[building_2_id]

        x1, y1 = building_1.x, building_1.y
        x2, y2 = building_2.x, building_2.y
        dx = x2 - x1
        dy = y2 - y1
        gcd = math.gcd(dx, dy)
        debug(x1, y1, x2, y2, gcd)
        step_x = x1
        step_y = y1
        for step in range(dx // gcd - 1):
            step_x += dx * gcd
            step_y += dy * gcd

            if (step_x, step_y) in self.buildings_by_coords:
                # There is a building at this coord
                return False

        # Make sure we wouldn't be intersecting with any other existing tube
        # TODO: Can this be improved instead of checking with every other existing tube?
        for other_tube in self.tubes.values():
            other_building_1 = self.buildings[other_tube.building_1_id]
            other_building_2 = self.buildings[other_tube.building_2_id]
            x3, y3 = other_building_1.x, other_building_1.y
            x4, y4 = other_building_2.x, other_building_2.y
            if segments_intersect(x1, y1, x2, y2, x3, y3, x4, y4):
                # This tube would intersect another tube
                return False

        # No reason why we couldn't build this tube!
        return True

# game loop
landing_pads = {}
modules = {}
buildings = {}
buildings_by_coords = {}
while True:
    resources = int(input())
    city = City(resources)
    city.landing_pads = landing_pads
    city.modules = modules
    city.buildings = buildings
    city.buildings_by_coords = buildings_by_coords

    # tubes: dict[tuple[int, int], Tube] = {}
    # teleporters: dict[tuple[int, int], Teleporter] = {}
    # pods: dict[int, Pod] = {}
    # landing_pads: dict[int, LandingPod] = {}
    # modules: dict[int, Module] = {}

    # buildings_by_coords: dict[tuple[int, int], LandingPod | Module] = {}

    num_travel_routes = int(input())
    for i in range(num_travel_routes):
        building_1_id, building_2_id, capacity = [int(j) for j in input().split()]
        if capacity == 0:
            teleporter = Teleporter(building_1_id, building_2_id)
            city.teleporters[(building_1_id, building_2_id)] = teleporter

            if building_1_id not in city.teleporters_by_building:
                city.teleporters_by_building[building_1_id] = []
            city.teleporters_by_building[building_1_id].append(teleporter)
            
            if building_2_id not in city.teleporters_by_building:
                city.teleporters_by_building[building_2_id] = []
            city.teleporters_by_building[building_2_id].append(teleporter)
        else: 
            tube = Tube(building_1_id, building_2_id, capacity)
            city.tubes[(building_1_id, building_2_id)] = tube
            city.tubes[(building_2_id, building_1_id)] = tube

            if building_1_id not in city.tubes_by_building:
                city.tubes_by_building[building_1_id] = []
            city.tubes_by_building[building_1_id].append(tube)

            if building_2_id not in city.tubes_by_building:
                city.tubes_by_building[building_2_id] = []
            city.tubes_by_building[building_2_id].append(tube)

    num_pods = int(input())
    for i in range(num_pods):
        pod_id, number_of_stops, *stops = [int(j) for j in input().split()]
        pod = Pod(pod_id, stops)
        city.pods[pod_id] = pod

    num_new_buildings = int(input())
    for i in range(num_new_buildings):
        module_type, *building_attributes = [int(j) for j in input().split()]
        if module_type == 0:
            building_id, x, y, total_astronauts, *astronaut_types = building_attributes
            astronauts: dict[int, int] = {}
            for astronaut in astronaut_types:
                if astronaut not in astronauts:
                    astronauts[astronaut] = 0
                astronauts[astronaut] += 1
            landing_pad = LandingPod(module_type, building_id, x, y, total_astronauts, astronauts)
            city.landing_pads[building_id] = landing_pad
            city.buildings[building_id] = landing_pad
            city.buildings_by_coords[(x, y)] = landing_pad
        else:
            building_id, x, y = building_attributes
            module = Module(module_type, building_id, x, y)
            city.modules[building_id] = module
            city.buildings[building_id] = module
            city.buildings_by_coords[(x, y)] = module

    # Write an action using print
    # To debug: print("Debug messages...", file=sys.stderr, flush=True)

    # TUBE | UPGRADE | TELEPORT | POD | DESTROY | WAIT
    start_time = time.time()
    output = turn(city)
    end_time = time.time()

    print(output)
    debug("Time elapsed:", end_time - start_time)
