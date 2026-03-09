from setuptools import find_packages, setup

package_name = 'grid_fleet'

setup(
    name=package_name,
    version='0.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='fares',
    maintainer_email='fares@todo.todo',
    description='TODO: Package description',
    license='Apache-2.0',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'vehicle_node = grid_fleet.vehicle_node:main',
            'temp_traffic_node = grid_fleet.temp_traffic:main',
        ],
    },
)
