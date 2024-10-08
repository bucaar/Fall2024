from dataclasses import dataclass, field
import sys
import math
import time
from collections import deque

ECHO_INPUT = False

MONTHS = 20
DAYS_PER_MONTH = 20

MAX_TUBES_PER_BUILDING = 5
MAX_TELEPORTERS_PER_BUILDING = 1
MAX_PASSENGERS_PER_POD = 10

TUBE_COST_PER_KM = .1
TELEPORTER_COST = 5000
POD_COST = 1000
POD_DESTROY_GAIN = 750

MODULE_TYPES = 20

SPEED_SCORE = 50
BALANCING_SCORE = 50

# TUBE | UPGRADE | TELEPORT | POD | DESTROY | WAIT
def turn(city: "City"):
    teleport_action(0, 1)
    tube_action(1, 2)

    debug("Path from 0->2?", city.path_exists(0, 2))
    debug("Path from 2->0?", city.path_exists(2, 0))

def tube_action(building_1_id: int, building_2_id: int):
    turn_actions.append(f"TUBE {building_1_id} {building_2_id}")

def upgrade_action(building_1_id: int, building_2_id: int):
    turn_actions.append(f"UPGRADE {building_1_id} {building_2_id}")

def teleport_action(building_entrance_id: int, building_exit_id: int):
    turn_actions.append(f"TELEPORT {building_entrance_id} {building_exit_id}")

def pod_action(pod_id: int, *building_ids: int):
    buildings = " ".join(building_ids)
    turn_actions.append(f"POD {pod_id} {buildings}")

def destroy_action(pod_id: int):
    turn_actions.append(f"DESTROY {pod_id}")

def wait_action():
    turn_actions.append(f"WAIT")

def dist_sq(x1: int, y1: int, x2: int, y2: int) -> int:
    return (x2 - x1) ** 2 + (y2 - y1) ** 2

def dist(x1: int, y1: int, x2: int, y2: int) -> float:
    return math.sqrt(dist_sq(x1, y1, x2, y2))

def segment_intervals(x1: int, y1: int, x2: int, y2: int):
    dx = x2 - x1
    dy = y2 - y1
    num_steps = math.gcd(dx, dy)
    x_step = dx // num_steps
    y_step = dy // num_steps
    for i in range(0, num_steps - 1):
        x1 += x_step
        y1 += y_step
        yield x1, y1

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

def get_tube_cost(x1: int, y1: int, x2: int, y2: int, capacity: int) -> int:
    tube_dist = dist(x1, y1, x2, y2)
    return math.floor(tube_dist / TUBE_COST_PER_KM) * capacity

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
    buildings_by_x: dict[int, list[LandingPod | Module]] = field(default_factory=dict)
    buildings_by_y: dict[int, list[LandingPod | Module]] = field(default_factory=dict)
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

        # Make sure this tube wouldn't intersect another building
        building_1 = self.buildings[building_1_id]
        building_2 = self.buildings[building_2_id]

        x1, y1 = building_1.x, building_1.y
        x2, y2 = building_2.x, building_2.y
        dx = x2 - x1
        dy = y2 - y1
        # If dx or dy is 0, it is probably more efficient to only check for buildings on that x/y band
        if dx == 0:
            for building in self.buildings_by_x[x1]:
                if building.y > building_1.y and building.y < building_2.y or \
                    building.y > building_2.y and building.y < building_1.y:
                    return False
        elif dy == 0:
            for building in self.buildings_by_y[y1]:
                if building.x > building_1.x and building.x < building_2.x or \
                    building.x > building_2.x and building.x < building_1.x:
                    return False
        else:
            for sx, sy in segment_intervals(x1, y1, x2, y2):
                if (sx, sy) in self.buildings_by_coords:
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

    def can_build_teleporter(self, building_1_id: int, building_2_id: int) -> bool:
        if building_1_id in self.teleporters_by_building and len(self.teleporters_by_building[building_1_id]) >= MAX_TELEPORTERS_PER_BUILDING:
            # Building 1 already has a teleporter
            return False
        
        if building_2_id in self.teleporters_by_building and len(self.teleporters_by_building[building_2_id]) >= MAX_TELEPORTERS_PER_BUILDING:
            # Building 2 already has a teleporter
            return False

        # No reason why we couldn't build this teleporter!
        return True
    
    def path_exists(self, building_1_id: int, building_2_id: int) -> bool:
        if building_1_id == building_2_id:
            # You're already there
            return True
        
        building_map: dict[int, int] = {}
        to_visit: deque[int] = deque([building_1_id])

        while to_visit:
            building_id = to_visit.popleft()
            # Just make sure this is a valid building..
            building = self.buildings[building_id]

            if building_id in self.teleporters_by_building:
                for teleporter in self.teleporters_by_building[building_id]:
                    # Teleporters are directional: 1 -> 2 only
                    if teleporter.building_1_id == building_id:
                        if teleporter.building_2_id not in building_map:
                            to_visit.append(teleporter.building_2_id)
                            building_map[teleporter.building_2_id] = building_id
                
            if building_id in self.tubes_by_building:
                for tube in self.tubes_by_building[building_id]:
                    # Tubes go in both directions
                    # But the tube has a defined 1 -> 2
                    # This building could be either one
                    if tube.building_1_id == building_id:
                        if tube.building_2_id not in building_map:
                            to_visit.append(tube.building_2_id)
                            building_map[tube.building_2_id] = building_id
                    elif tube.building_2_id == building_id:
                        if tube.building_1_id not in building_map:
                            to_visit.append(tube.building_1_id)
                            building_map[tube.building_1_id] = building_id
                    else:
                        raise RuntimeError("Should be building 1 or 2?")
                    
            if building_2_id in building_map:
                # TODO: Do we care about the actual path? That kinda depends on the pods and astronauts?
                return True
        
        # We explored every path, did not find a way to get to building 2 :(
        return False

def read():
    line = input()
    if ECHO_INPUT:
        debug(line)
    return line

# game loop
landing_pads: dict[int, LandingPod] = {}
modules: dict[int, Module] = {}
buildings: dict[int, LandingPod | Module] = {}
buildings_by_coords: dict[tuple[int, int], LandingPod | Module] = {}
buildings_by_x: dict[int, list[LandingPod | Module]] = {}
buildings_by_y: dict[int, list[LandingPod | Module]] = {}
turn_actions: list[str] = []
while True:
    start_time = time.time()
    resources = int(read())
    city = City(resources)
    city.landing_pads = landing_pads
    city.modules = modules
    city.buildings = buildings
    city.buildings_by_coords = buildings_by_coords
    city.buildings_by_x = buildings_by_x
    city.buildings_by_y = buildings_by_y

    num_travel_routes = int(read())
    for i in range(num_travel_routes):
        building_1_id, building_2_id, capacity = [int(j) for j in read().split()]
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

    num_pods = int(read())
    for i in range(num_pods):
        pod_id, number_of_stops, *stops = [int(j) for j in read().split()]
        pod = Pod(pod_id, stops)
        city.pods[pod_id] = pod

    num_new_buildings = int(read())
    for i in range(num_new_buildings):
        module_type, *building_attributes = [int(j) for j in read().split()]
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
            if x not in city.buildings_by_x:
                city.buildings_by_x[x] = []
            city.buildings_by_x[x].append(landing_pad)
            if y not in city.buildings_by_y:
                city.buildings_by_y[y] = []
            city.buildings_by_y[y].append(landing_pad)
        else:
            building_id, x, y = building_attributes
            module = Module(module_type, building_id, x, y)
            city.modules[building_id] = module
            city.buildings[building_id] = module
            city.buildings_by_coords[(x, y)] = module
            if x not in city.buildings_by_x:
                city.buildings_by_x[x] = []
            city.buildings_by_x[x].append(module)
            if y not in city.buildings_by_y:
                city.buildings_by_y[y] = []
            city.buildings_by_y[y].append(module)
    end_time = time.time()
    debug("Setup time elapsed (ms):", (end_time - start_time) * 1000)

    start_time = time.time()
    turn(city)
    end_time = time.time()

    output = ";".join(turn_actions)
    turn_actions.clear()

    print(output)
    debug("Turn time elapsed (ms):", (end_time - start_time) * 1000)
