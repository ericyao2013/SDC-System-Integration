#!/usr/bin/env python

import rospy
import tf
from geometry_msgs.msg import PoseStamped
from styx_msgs.msg import Lane, Waypoint
import numpy as np
import copy

import math

'''
This node will publish waypoints from the car's current position to some `x` distance ahead.

As mentioned in the doc, you should ideally first implement a version which does not care
about traffic lights or obstacles.

Once you have created dbw_node, you will update this node to use the status of traffic lights too.

Please note that our simulator also provides the exact location of traffic lights and their
current status in `/vehicle/traffic_lights` message. You can use this message to build this node
as well as to verify your TL classifier.

TODO (for Yousuf and Aaron): Stopline location for each traffic light.
'''

LOOKAHEAD_WPS = 200 # Number of waypoints we will publish. You can change this number


class WaypointUpdater(object):
    def __init__(self):
        rospy.init_node('waypoint_updater')

        rospy.Subscriber('/current_pose', PoseStamped, self.pose_cb)
        rospy.Subscriber('/base_waypoints', Lane, self.waypoints_cb)

        # TODO: Add a subscriber for /traffic_waypoint and /obstacle_waypoint below
        # NOTE: comment out until we get traffic lights working...
        # rospy.Subscriber('/traffic_waypoint', Waypoint, self.traffic_cb)
        # rospy.Subscriber('/obstacle_waypoint', Waypoint, self.obstacle_cb)

        self.final_waypoints_pub = rospy.Publisher('final_waypoints', Lane, queue_size=1)

        # DONE: Add other member variables you need below
        self.updateRate = 2 # update 2 times a second
        self.pose = None
        self.theta = None
        self.waypoints = None
        self.cwp = None
        self.i = 0

        self.loop()

    def loop(self):
        rate = rospy.Rate(self.updateRate)
        while not rospy.is_shutdown():
            if self.waypoints and self.theta:
                self.nextWaypoint()
                print self.i, "self.cwp:", self.cwp
                print ""
                self.getWaypoints(LOOKAHEAD_WPS)
                self.publish()
        rate.sleep()

    def pose_cb(self, msg):
        # DONE: Implement
        self.i += 1
        self.pose = msg
        self.position = msg.pose.position
        self.orientation = msg.pose.orientation
        euler = tf.transformations.euler_from_quaternion([
            self.orientation.x,
            self.orientation.y,
            self.orientation.z,
            self.orientation.w])
        self.theta = euler[2]
        
    def nextWaypoint(self):
        dist = 100000.
        dl = lambda a, b: math.sqrt((a.x-b.x)**2 + (a.y-b.y)**2  + (a.z-b.z)**2)
        cwp = 0
        for i in range(len(self.waypoints)):
            d1 = dl(self.position, self.waypoints[i].pose.pose.position)
            if dist > d1:
                cwp = i
                dist = d1
        x = self.waypoints[cwp].pose.pose.position.x
        y = self.waypoints[cwp].pose.pose.position.y
        heading = np.arctan2((y-self.position.y), (x-self.position.x))
        angle = np.abs(self.theta-heading)
        if angle > np.pi/4.:
            cwp += 1
            if cwp >= len(self.waypoints):
                cwp = 0
        self.cwp = cwp

    def getWaypoints(self, number):
        self.final_waypoints = []
        vptsx = []
        vptsy = []
        wlen = len(self.waypoints)

        # change to local coordinates
        for i in range(number):
            vx = self.waypoints[(i+self.cwp)%wlen].pose.pose.position.x - self.position.x
            vy = self.waypoints[(i+self.cwp)%wlen].pose.pose.position.y - self.position.y
            lx = vx*np.cos(self.theta) + vy*np.sin(self.theta)
            ly = -vx*np.sin(self.theta) + vy*np.cos(self.theta)
            vptsx.append(lx)
            vptsy.append(ly)
            self.final_waypoints.append(self.waypoints[(i+self.cwp)%wlen])

        # calculate cross track error (cte)
        poly = np.polyfit(np.array(vptsx), np.array(vptsy), 3)
        polynomial = np.poly1d(poly)
        mps = 0.44704
        for i in range(len(vptsx)):
            cte = polynomial([vptsx[i]])[0]
            self.final_waypoints[i].twist.twist.linear.x = mps*25.
            self.final_waypoints[i].twist.twist.angular.z = cte

    def waypoints_cb(self, msg):
        # DONE: Implement
        if self.waypoints is None:
            self.waypoints = []
            for waypoint in msg.waypoints:
                self.waypoints.append(waypoint)

            # make sure we wrap and correct for angles!
            lastx = self.waypoints[len(msg.waypoints)-1].pose.pose.position.x
            lasty = self.waypoints[len(msg.waypoints)-1].pose.pose.position.y
            self.waypoints.append(msg.waypoints[0])
            x = self.waypoints[len(msg.waypoints)-1].pose.pose.position.x
            y = self.waypoints[len(msg.waypoints)-1].pose.pose.position.y
            self.waypoints[len(self.waypoints)-1].twist.twist.angular.z = np.arctan2((y-lasty), (x-lastx))
            lastx = x
            lasty = y
            self.waypoints.append(msg.waypoints[1])
            x = self.waypoints[len(msg.waypoints)-1].pose.pose.position.x
            y = self.waypoints[len(msg.waypoints)-1].pose.pose.position.y
            self.waypoints[len(self.waypoints)-1].twist.twist.angular.z = np.arctan2((y-lasty), (x-lastx))

    def traffic_cb(self, msg):
        # TODO: Callback for /traffic_waypoint message. Implement
        pass

    def obstacle_cb(self, msg):
        # TODO: Callback for /obstacle_waypoint message. We will implement it later
        pass

    def get_waypoint_velocity(self, waypoint):
        return waypoint.twist.twist.linear.x

    def set_waypoint_velocity(self, waypoints, waypoint, velocity):
        waypoints[waypoint].twist.twist.linear.x = velocity

    def distance(self, waypoints, wp1, wp2):
        dist = 0
        dl = lambda a, b: math.sqrt((a.x-b.x)**2 + (a.y-b.y)**2  + (a.z-b.z)**2)
        for i in range(wp1, wp2+1):
            dist += dl(waypoints[wp1].pose.pose.position, waypoints[i].pose.pose.position)
            wp1 = i
        return dist

    def publish(self):
        lane = Lane()
        lane.header.frame_id = '/world'
        lane.header.stamp = rospy.Time(0)
        lane.waypoints = self.final_waypoints
        self.final_waypoints_pub.publish(lane)


if __name__ == '__main__':
    try:
        WaypointUpdater()
    except rospy.ROSInterruptException:
        rospy.logerr('Could not start waypoint updater node.')
