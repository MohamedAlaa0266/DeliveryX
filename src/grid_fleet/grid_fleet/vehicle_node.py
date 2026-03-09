#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from grid_fleet_msgs.srv import TaskRequest, MoveRequest
from std_msgs.msg import String, Int32MultiArray
import sys
import re

class VehicleNode(Node):
    def __init__(self, vehicle_id, x=0, y=0):
        # Naming the node 'vehicle_1', 'vehicle_2', etc.
        super().__init__(f'vehicle_{vehicle_id}')
        self.vehicle_id = vehicle_id

        # State and Grid Position
        self.state = 'IDLE'
        self.position = [int(x), int(y)]
        self.target_position = None
        self.task = {}
        self.previous_state = ""

        # Publishers
        self.state_pub = self.create_publisher(String, '/vehicle_state', 10)
        self.position_pub = self.create_publisher(Int32MultiArray, '/vehicle_position', 10)

        # Services
        self.task_client = self.create_client(TaskRequest, '/request_task')
        self.move_client = self.create_client(MoveRequest, '/request_move')

        # Timer
        self.timer = self.create_timer(1.0, self.control_loop)
        self.get_logger().info(f'Position: {self.position}')

    def control_loop(self):
        self.publish_state()

        if self.state == 'IDLE':
            self.get_task()
        
        elif self.state == "MOVING_TO_PICKUP" and self.task:
            self.move_logic(self.task.get('pickup'), "MOVING_TO_DROPOFF")

        elif self.state == "MOVING_TO_DROPOFF" and self.task:
            self.move_logic(self.task.get('dropoff'), "FINISHED")

        elif self.state == "FINISHED":
            self.get_logger().info("Task completed")
            self.state = "IDLE"

        elif self.state == "WAITING" and self.task:
            target = self.task['pickup'] if self.previous_state == "MOVING_TO_PICKUP" else self.task['dropoff']
            next_state_after_wait = "MOVING_TO_DROPOFF" if self.previous_state == "MOVING_TO_PICKUP" else "FINISHED"
            self.move_logic(target, next_state_after_wait)

    def publish_state(self):
        pub_msg = Int32MultiArray()
        pub_msg.data = [self.vehicle_id, self.position[0], self.position[1]]
        self.position_pub.publish(pub_msg)

        state_msg = String()
        # Cleaned output: "1: IDLE" instead of "Vehiclevehicle1: IDLE"
        state_msg.data = f"{self.vehicle_id}: {self.state}"
        self.state_pub.publish(state_msg)

    def get_task(self):
        if not self.task_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().error(f'Task service not available, position: {self.position}')
            return
        req = TaskRequest.Request()
        future = self.task_client.call_async(req)
        future.add_done_callback(self.task_callback)

    def task_callback(self, future):
        res = future.result()
        if res.success:
            self.task = {
                'pickup': [res.pickup_x, res.pickup_y],
                'dropoff': [res.dropoff_x, res.dropoff_y]
            }
            self.state = "MOVING_TO_PICKUP"
            self.get_logger().info(f"New Task: Go to {self.task['pickup']}")

    def move_logic(self, target, next_state):
        if self.position == target:
            self.state = next_state
            return
        
        next_step = list(self.position)
        if next_step[0] < target[0]: next_step[0] += 1
        elif next_step[0] > target[0]: next_step[0] -= 1
        elif next_step[1] < target[1]: next_step[1] += 1
        elif next_step[1] > target[1]: next_step[1] -= 1

        self.request_move(next_step)

    def request_move(self, next_step):
        if not self.move_client.wait_for_service(timeout_sec=1.0):
            return
        req = MoveRequest.Request()
        req.vehicle_id = str(self.vehicle_id)
        req.target_x = next_step[0]
        req.target_y = next_step[1]
        future = self.move_client.call_async(req)
        future.add_done_callback(lambda f: self.move_callback(f, next_step))

    def move_callback(self, future, next_step):
        res = future.result()
        if res.approved:
            self.position = next_step
            if self.state == 'WAITING':
                self.state = self.previous_state
        else:
            if hasattr(res, 'alternative_x') and res.alternative_x != -1:
                self.position = [res.alternative_x, res.alternative_y]
                self.get_logger().info(f"Taking alternative path to ({res.alternative_x}, {res.alternative_y})")
                if self.state == 'WAITING':
                    self.state = self.previous_state
            else:
                if self.state != 'WAITING':
                    self.previous_state = self.state
                    self.state = 'WAITING'
                self.get_logger().info("Move blocked by Traffic Controller. Waiting.")

def main(args=None):
    rclpy.init(args=args)
    
    # Filter ROS internal args
    from rclpy.utilities import remove_ros_args
    clean_args = remove_ros_args(args=sys.argv)
    
    v_id = clean_args[1] if len(clean_args) > 1 else "1"

    try:
        # Strip letters so 'vehicle2' becomes 2 for math
        numeric_id = re.sub(r'\D', '', v_id)
        id_num = int(numeric_id) if numeric_id else 1
        start_x = id_num - 1
        start_y = 0
    except Exception:
        start_x, start_y = 0, 0

    node = VehicleNode(id_num, start_x, start_y)
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info(f'Shutting down vehicle {v_id}...')
    finally:
        if rclpy.ok():
            node.destroy_node()
            rclpy.shutdown()

if __name__ == '__main__':
    main()