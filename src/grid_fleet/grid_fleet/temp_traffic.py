#!/usr/bin/env python3
# this is a temporary file to test traffic I will delete it later

import rclpy
from rclpy.node import Node
from grid_fleet_msgs.srv import MoveRequest

class DummyTrafficController(Node):
    def __init__(self):
        super().__init__('traffic_controller')
        self.srv = self.create_service(MoveRequest, '/request_move', self.handle_move)
        self.get_logger().info("Traffic Controller is ONLINE. All moves will be approved.")

    def handle_move(self, request, response):
        self.get_logger().info(f"Approving move to [{request.target_x}, {request.target_y}]")
        response.approved = True
        return response

def main():
    rclpy.init()
    node = DummyTrafficController()
    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == '__main__':
    main()
    