import rclpy
from rclpy.node import Node
from grid_fleet_msgs.srv import TaskRequest
import sys

def main(args=None):
    rclpy.init(args=args)
    node = rclpy.create_node('Vehicle_Client_Test')
    
    # Connect to your service name
    client = node.create_client(TaskRequest, '/request_task')
    
    while not client.wait_for_service(timeout_sec=1.0):
        node.get_logger().info("Service /request_task not available. Waiting...")

    # YOUR TaskRequest.srv has no input fields, so we just create an empty request
    request = TaskRequest.Request()

    # Call the service
    future = client.call_async(request)
    rclpy.spin_until_future_complete(node, future)

    try:
        resp = future.result()
        if resp.success:
            # Mapping your specific field names
            print(f"--- Task Received ---")
            print(f"Pick-up:  ({resp.pickup_x}, {resp.pickup_y})")
            print(f"Drop-off: ({resp.dropoff_x}, {resp.dropoff_y})")
        else:
            print("Manager returned success=False. No task assigned.")
    except Exception as e:
        node.get_logger().error(f"Service call failed: {e}")

    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()