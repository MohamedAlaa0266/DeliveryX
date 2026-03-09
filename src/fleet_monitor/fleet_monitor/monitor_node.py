import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from std_msgs.msg import Int32MultiArray
import time
import curses

class MonitorNode(Node):
    def __init__(self, stdscr):
        super().__init__('monitor_node')
        
        self.stdscr = stdscr
        # Initialize curses colors
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_BLUE, -1)    # IDLE
        curses.init_pair(2, curses.COLOR_YELLOW, -1)  # PICKUP
        curses.init_pair(3, curses.COLOR_GREEN, -1)   # DROPOFF
        curses.init_pair(4, curses.COLOR_MAGENTA, -1) # WAITING
        curses.init_pair(5, curses.COLOR_CYAN, -1)    # FINISHED
        curses.init_pair(6, curses.COLOR_RED, -1)     # ERROR/WARNING
        
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

    def position_callback(self, msg):
        vehicle_id = msg.data[0]
        x = msg.data[1]
        y = msg.data[2]
        self.positions[vehicle_id] = (x, y)
        self.last_move_time[vehicle_id] = time.time()

    def state_callback(self, msg):
        try:
            parts = msg.data.split(': ')
            vehicle_id = int(parts[0])
            state = parts[1]
            self.states[vehicle_id] = state
        except Exception:
            pass

    def get_state_info(self, state):
        mapping = {
            'IDLE': ('I', 1),
            'MOVING_TO_PICKUP': ('P', 2),
            'MOVING_TO_DROPOFF': ('D', 3),
            'WAITING': ('W', 4),
            'FINISHED': ('F', 5)
        }
        return mapping.get(state, ('?', 6))

    def draw_ui(self):
        self.stdscr.clear()
        max_y, max_x = self.stdscr.getmaxyx()
        
        # Header
        header = "===== ROS 2 Fleet Monitor ====="
        self.stdscr.addstr(0, max_x // 2 - len(header) // 2, header, curses.A_BOLD)
        
        # Layout bounds
        table_start_y = 2
        grid_start_y = 2
        grid_start_x = max_x // 2 + 5
        
        # --- Draw Table ---
        self.stdscr.addstr(table_start_y, 2, f"{'ID':<4} | {'State':<18} | {'Pos':<8} | {'Wait (s)':<8}", curses.A_UNDERLINE)
        
        current_time = time.time()
        stuck_warnings = []
        
        row_idx = table_start_y + 1
        for vid in sorted(self.states.keys()):
            if row_idx >= max_y - 3: 
                break # terminal too small
                
            state = self.states.get(vid, "UNKNOWN")
            pos = self.positions.get(vid, ("?", "?"))
            symbol, color = self.get_state_info(state)
            
            elapsed = 0.0
            if vid in self.last_move_time:
                elapsed = current_time - self.last_move_time[vid]
                if elapsed > 10 and state not in ['IDLE', 'FINISHED']:
                    stuck_warnings.append((vid, elapsed))
            
            self.stdscr.addstr(row_idx, 2, f"{vid:<4} | ")
            self.stdscr.addstr(row_idx, 9, f"{state:<18}", curses.color_pair(color))
            self.stdscr.addstr(row_idx, 29, f"| {str(pos):<8} | {elapsed:>6.1f}")
            row_idx += 1

        # --- Draw Grid ---
        grid_size = 8
        if grid_start_x + (grid_size * 4) < max_x:
            self.stdscr.addstr(grid_start_y, grid_start_x, "Grid View (8x8)", curses.A_BOLD)
            
            # Map vehicles to cells
            grid_map = {}
            for vid, pos in self.positions.items():
                x, y = pos
                if 0 <= x < grid_size and 0 <= y < grid_size:
                    grid_map[(x, y)] = vid

            # Draw Y axises and Cells (y=0 at bottom)
            for visual_y in range(grid_size):
                actual_y = grid_size - 1 - visual_y
                draw_y = grid_start_y + 2 + visual_y
                
                self.stdscr.addstr(draw_y, grid_start_x - 3, f"{actual_y:2}") # Y axis label
                
                for x in range(grid_size):
                    vid = grid_map.get((x, actual_y))
                    draw_x = grid_start_x + (x * 4)
                    
                    if vid is not None:
                        state = self.states.get(vid, "UNKNOWN")
                        symbol, color = self.get_state_info(state)
                        text = f"{vid}{symbol}"
                        self.stdscr.addstr(draw_y, draw_x, f"{text:^4}", curses.color_pair(color) | curses.A_BOLD)
                    else:
                        self.stdscr.addstr(draw_y, draw_x, f"{'.':^4}", curses.A_DIM)
            
            # Draw X axis labels
            draw_y_x_axis = grid_start_y + 2 + grid_size
            for x in range(grid_size):
                self.stdscr.addstr(draw_y_x_axis, grid_start_x + (x * 4), f"{x:^4}")
                
            # Draw Legend
            legend_y = draw_y_x_axis + 2
            if legend_y < max_y - 2:
                leg_x = grid_start_x
                self.stdscr.addstr(legend_y, leg_x, "I=IDLE ", curses.color_pair(1))
                self.stdscr.addstr(legend_y, leg_x+7, "P=PICKUP ", curses.color_pair(2))
                self.stdscr.addstr(legend_y, leg_x+16, "D=DROPOFF ", curses.color_pair(3))
                self.stdscr.addstr(legend_y, leg_x+26, "W=WAITING ", curses.color_pair(4))
                self.stdscr.addstr(legend_y, leg_x+36, "F=FINISHED", curses.color_pair(5))

        # --- Draw Warnings ---
        warn_y = max(row_idx + 2, grid_start_y + grid_size + 4)
        if stuck_warnings and warn_y < max_y:
            self.stdscr.addstr(warn_y, 2, "WARNINGS:", curses.color_pair(6) | curses.A_BOLD)
            warn_y += 1
            for i, (vid, elapsed) in enumerate(stuck_warnings):
                if warn_y + i >= max_y: break
                self.stdscr.addstr(warn_y + i, 4, f"Vehicle {vid} stuck for {elapsed:.1f}s", curses.color_pair(6))

        self.stdscr.refresh()

def monitor_loop(stdscr):
    # Setup Curses input
    stdscr.nodelay(True)
    curses.curs_set(0) # Hide cursor
    
    # Init ROS inside the wrapper
    rclpy.init(args=None)
    node = MonitorNode(stdscr)
    
    # Keep track of last drawn state to avoid flickering
    last_drawn_time = 0
    last_known_positions = {}
    last_known_states = {}
    
    # Main Loop
    try:
        while rclpy.ok():
            rclpy.spin_once(node, timeout_sec=0.1)
            
            # Check if we need to redraw:
            # 1. Positions changed
            # 2. States changed
            # 3. 1 second passed (to update warning timers smoothly)
            current_time = time.time()
            needs_redraw = False
            
            if node.positions != last_known_positions or node.states != last_known_states:
                needs_redraw = True
                last_known_positions = node.positions.copy()
                last_known_states = node.states.copy()
            elif current_time - last_drawn_time > 1.0:
                needs_redraw = True
                
            if needs_redraw:
                node.draw_ui()
                last_drawn_time = current_time
            
            # Allows clean exit with 'q'
            c = stdscr.getch()
            if c == ord('q'):
                break
                
    finally:
        node.destroy_node()
        rclpy.shutdown()

def main(args=None):
    curses.wrapper(monitor_loop)

if __name__ == '__main__':
    main()