import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from std_msgs.msg import Int32MultiArray
import time
import os
RESET = "\033[0m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
BOLD = "\033[1m"

class MonitorNode(Node):

    def __init__(self):
        
        super().__init__('monitor_node')
        print("\033[2J", end="")
        
        self.positions = {}
        self.states = {}
        self.last_move_time = {}

        self.position_subscriber = self.create_subscription(
            Int32MultiArray,
            '/vehicle_position',
            self.position_callback,
            10
        )

        self.state_subscriber = self.create_subscription(
            String,
            '/vehicle_state',
            self.state_callback,
            10
        )

        self.timer = self.create_timer(0.1, self.monitor_system)

        self.get_logger().info("Monitor Node Started")


    def position_callback(self, msg):

        vehicle_id = msg.data[0]
        x = msg.data[1]
        y = msg.data[2]

        self.positions[vehicle_id] = (x, y)
        self.last_move_time[vehicle_id] = time.time()


    def state_callback(self, msg):

        parts = msg.data.split(': ')

        vehicle_id = int(parts[0])
        state = parts[1]

        self.states[vehicle_id] = state
#-------------------------Grid------------------------------#
    def state_symbol(self, state):
        if state == 'IDLE':
            return 'I'
        elif state == 'MOVING_TO_PICKUP':
            return 'P'
        elif state == 'MOVING_TO_DROPOFF':
            return 'D'
        elif state == 'WAITING':
            return 'W'
        elif state == 'FINISHED':
            return 'F'
        else:
            return '?'

    # def draw_grid(self):
    #     grid_size = 8
    #     grid = [[' .' for _ in range(grid_size)] for _ in range(grid_size)]

    #     for vid, pos in self.positions.items():
    #         x, y = pos

    #         if 0 <= x < grid_size and 0 <= y < grid_size:
    #             state = self.states.get(vid, 'UNKNOWN')
    #             symbol = self.state_symbol(state)
    #             grid[y][x] = f'{vid}{symbol}'

    #     print("\nGrid View (8x8)")
    #     print("Legend: I=IDLE, P=PICKUP, D=DROPOFF, W=WAITING, F=FINISHED\n")

    #     header = "    " + "".join(f"{x:>3}" for x in range(grid_size))
    #     print(header)

    #     for y in range(grid_size):
    #         row = f"{y:>3} "
    #         for x in range(grid_size):
    #             row += f"{grid[y][x]:>3}"
    #         print(row)
    def draw_grid(self):
        grid_size = 8

        # Empty grid: None means empty cell
        grid = [[None for _ in range(grid_size)] for _ in range(grid_size)]

        # Place vehicles
        for vid, pos in self.positions.items():
            x, y = pos

            if 0 <= x < grid_size and 0 <= y < grid_size:
                state = self.states.get(vid, 'UNKNOWN')
                grid[y][x] = (vid, state)

        print(f"{BOLD}Grid View (8x8){RESET}")
        print(
            f"Legend: "
            f"{BLUE}I=IDLE{RESET}, "
            f"{YELLOW}P=PICKUP{RESET}, "
            f"{GREEN}D=DROPOFF{RESET}, "
            f"{MAGENTA}W=WAITING{RESET}, "
            f"{CYAN}F=FINISHED{RESET}\n"
        )

        

        for y in range(grid_size-1,-1,-1):
            row = f"{y:^4}"

            for x in range(grid_size):
                cell = grid[y][x]

                if cell is None:
                    row += f"{'.':^4}"
                else:
                    vid, state = cell
                    symbol = self.state_symbol(state)
                    color = self.state_color(state)
                    row += f"{color}{(str(vid) + symbol):^4}{RESET}"

            print(row)
        print()
        header = "    "
        for x in range(grid_size):
            header += f"{x:^4}"
        print(header)
#--------------------------------------------------------------#


    # def monitor_system(self):
        
    #     print("\033[H\033[J", end="")

    #     print("===== Fleet Monitor =====\n")

    #     for vid in sorted(self.states.keys()):
    #         state = self.states.get(vid, "UNKNOWN")
    #         pos = self.positions.get(vid, ("?", "?"))
    #         print(f"Vehicle {vid} | State: {state:<18} | Position: {str(pos):<8}")

    #     print()
    #     self.draw_grid()
    #     print()
    #     self.detect_stuck()
    def monitor_system(self):
        print("\033[H\033[J", end="")

        print(f"{BOLD}===== Fleet Monitor ====={RESET}\n")

        for vid in sorted(self.states.keys()):
            state = self.states.get(vid, "UNKNOWN")
            pos = self.positions.get(vid, ("?", "?"))
            color = self.state_color(state)

            print(
                f"Vehicle {vid} | "
                f"State: {color}{state:<18}{RESET} | "
                f"Position: {str(pos):<8}"
            )

        print()
        self.draw_grid()
        print()
        self.detect_stuck()


    # def detect_stuck(self):

    #     current_time = time.time()

    #     for vid in self.last_move_time:

    #         elapsed = current_time - self.last_move_time[vid]

    #         if elapsed > 10: 

    #             print(f"WARNING: Vehicle {vid} stuck for {elapsed:.1f} seconds")
    def detect_stuck(self):
        current_time = time.time()

        for vid in self.last_move_time:
            elapsed = current_time - self.last_move_time[vid]

            if elapsed > 10:
                print(f"{RED}WARNING: Vehicle {vid} stuck for {elapsed:.1f} seconds{RESET}")


    
    def state_color(self, state):
        if state == 'IDLE':
            return BLUE
        elif state == 'MOVING_TO_PICKUP':
            return YELLOW
        elif state == 'MOVING_TO_DROPOFF':
            return GREEN
        elif state == 'WAITING':
            return MAGENTA
        elif state == 'FINISHED':
            return CYAN
        else:
            return RED
        


def main(args=None):

    rclpy.init(args=args)

    node = MonitorNode()

    rclpy.spin(node)

    node.destroy_node()

    rclpy.shutdown()


if __name__ == '__main__':
    main()