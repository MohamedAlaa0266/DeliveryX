#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from grid_fleet_msgs.srv import MoveRequest
from std_msgs.msg import Int32MultiArray
import random

class TrafficControllerNode(Node):
    def __init__(self):
        super().__init__('traffic_controller')
        
        self.positions = {}
        self.wait_counts = {}
        self.GRID_SIZE = 8
        self.DEADLOCK_THRESHOLD = 3
        
        # Subscribe to positions to maintain occupancy map
        self.pos_sub = self.create_subscription(
            Int32MultiArray,
            '/vehicle_position',
            self.position_callback,
            10
        )
        
        # Service for move requests
        self.srv = self.create_service(MoveRequest, '/request_move', self.handle_move)
        
        self.get_logger().info("Traffic Controller is ONLINE. Collision & Deadlock prevention activated.")

    def position_callback(self, msg):
        v_id = str(msg.data[0])
        x = msg.data[1]
        y = msg.data[2]
        self.positions[v_id] = (x, y)

    def handle_move(self, request, response):
        v_id = str(request.vehicle_id)
        target = (request.target_x, request.target_y)
        response.alternative_x = -1
        response.alternative_y = -1
        
        if v_id not in self.wait_counts:
            self.wait_counts[v_id] = 0

        # Check if target is currently occupied
        occupied = False
        for other_id, pos in self.positions.items():
            if other_id != v_id and pos == target:
                occupied = True
                break
                
        if not occupied:
            # Target is free
            response.approved = True
            self.wait_counts[v_id] = 0
            self.get_logger().info(f"Move Approved: Vehicle {v_id} to {target}")
            # Speculatively update position to avoid race conditions
            self.positions[v_id] = target
        else:
            # Target is occupied
            response.approved = False
            self.wait_counts[v_id] += 1
            self.get_logger().info(f"Move Rejected: Vehicle {v_id} to {target} (Occupied). Wait count: {self.wait_counts[v_id]}")
            
            # Deadlock prevention logic
            if self.wait_counts[v_id] >= self.DEADLOCK_THRESHOLD:
                self.get_logger().warn(f"Deadlock detected for Vehicle {v_id}. Finding alternative route.")
                
                # Try to find a free adjacent space
                current_pos = self.positions.get(v_id)
                if current_pos:
                    cx, cy = current_pos
                    candidates = [
                        (cx + 1, cy), (cx - 1, cy),
                        (cx, cy + 1), (cx, cy - 1)
                    ]
                    random.shuffle(candidates)
                    
                    for cand_x, cand_y in candidates:
                        # Ensure within bounds
                        if 0 <= cand_x < self.GRID_SIZE and 0 <= cand_y < self.GRID_SIZE:
                            # Check if cand is occupied
                            cand_occupied = False
                            for other_id, pos in self.positions.items():
                                if pos == (cand_x, cand_y):
                                    cand_occupied = True
                                    break
                            
                            if not cand_occupied:
                                response.alternative_x = cand_x
                                response.alternative_y = cand_y
                                self.wait_counts[v_id] = 0 # reset to give it a chance
                                self.positions[v_id] = (cand_x, cand_y) # speculative
                                self.get_logger().info(f"Alternative Route assigned for {v_id}: ({cand_x}, {cand_y})")
                                break
                                
        return response

def main(args=None):
    rclpy.init(args=args)
    node = TrafficControllerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('Shutting down traffic controller...')
    finally:
        if rclpy.ok():
            node.destroy_node()
            rclpy.shutdown()

if __name__ == '__main__':
    main()
