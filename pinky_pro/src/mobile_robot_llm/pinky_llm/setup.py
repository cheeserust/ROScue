from setuptools import find_packages, setup
from glob import glob
import os

package_name = 'pinky_llm'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name, ['pinky_llm/.env']),
        ('share/' + package_name, ['pinky_llm/robot_tools.py',]),
        (os.path.join('share', package_name, 'launch'),
            glob('launch/*')),
        (os.path.join('share', package_name, 'map'),
            glob('map/*')),
        ('share/' + package_name + '/params',[
            'params/prompt.yaml',
            'params/points.yaml',
        ]),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='subin',
    maintainer_email='subin@todo.todo',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'agent_service = pinky_llm.agent_service:main',
            'agent_client = pinky_llm.agent_client:main',
        ],
    },
)
