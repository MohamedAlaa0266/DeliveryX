import rclpy
from rclpy.node import Node
from grid_fleet_msgs.srv import TaskRequest
import numpy as np

class TaskManager(Node):
    def __init__(self):
        super().__init__('Task_Manager')
        self.task_list = []
        self.task_index = 0
        self.task_completed = 0
        
        # Create the service using YOUR service name and type
        self.srv = self.create_service(TaskRequest, '/request_task', self.request_task_callback)
        
        self.create_tasks()
        self.get_logger().info('Task Manager is active and waiting for vehicles...')

    def create_tasks(self):
        # Generate 10 random tasks on an 8x8 grid
        self.task_list = np.random.randint(0, 8, size=(10, 4))
        for i in range(10):
            # Ensure pickup and dropoff aren't the same spot
            while (self.task_list[i][0] == self.task_list[i][2] and 
                   self.task_list[i][1] == self.task_list[i][3]):
                self.task_list[i][2] = np.random.randint(0, 8)
                self.task_list[i][3] = np.random.randint(0, 8)

    def request_task_callback(self, request, response):
        # If we run out of tasks, generate a new batch
        if self.task_index >= len(self.task_list):
            self.create_tasks()
            self.task_index = 0

        # Map their logic to your .srv fields
        current_task = self.task_list[self.task_index]
        response.pickup_x = int(current_task[0])
        response.pickup_y = int(current_task[1])
        response.dropoff_x = int(current_task[2])
        response.dropoff_y = int(current_task[3])
        response.success = True  # Crucial for your VehicleNode state transition
        
        self.get_logger().info(f'Assigned Task {self.task_index}: Pick up at [{response.pickup_x}, {response.pickup_y}]')
        
        self.task_index += 1
        return response

def main(args=None):
    rclpy.init(args=args)
    node = TaskManager()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()