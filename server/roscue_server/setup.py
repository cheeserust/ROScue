from setuptools import find_packages, setup

package_name = 'roscue_server'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='a',
    maintainer_email='gammastellapasta@gmail.com',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            "roscue_central_server = roscue_server.roscue_central_server_node:main",
            'server_omx_manual_control = roscue_server.server_omx_manual_control:main',
            'omx_camera_position_script = roscue_server.omx_camera_position_script:main',
            'roscue_service_relay = roscue_server.roscue_service_relay:main',
            'yolo_gateway = roscue_server.yolo_gateway:main',
        ],
    },
)
