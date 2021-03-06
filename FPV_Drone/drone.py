import ac
import math
from values import AppState, Values
from controller import Input
# import FPV_Drone

def dot(v1, v2):
    return v1[0]*v2[0]+v1[1]*v2[1]+v1[2]*v2[2]

def mag(v1):
    return math.sqrt(v1[0]*v1[0]+v1[1]*v1[1]+v1[2]*v1[2])

class DroneState:
    position = [0, 0, 0]
    velocity = [0, 0, 0]
    isAsleep = False

def airDrag(density, speed, coefficient, area, minAreaCoeff, angle):
    areaCoeff = math.cos(angle*2)/2*(1-minAreaCoeff)+(1-(1-minAreaCoeff)/2) # c=1 at 0 and 180 degrees and c=minAreaCoeff at 90 degrees
    # FPV_Drone.console(areaCoeff)
    return (density*(5*coefficient)*area*areaCoeff)/2*speed*abs(speed)

def throttleForce(motorKv, throttle, inflowVelocity):
    if not Values.linearAcceleration:
        a = Values.airDensity*(3.14*((0.0254*Values.propDiameter)**2)/4)*((Values.propDiameter/(3.29547*(Values.propPitch+0.5)))**1.5)*1.5*4
        maxRPM = min(motorKv*Values.batteryCells*3.7*(5.4/(Values.propDiameter**1.1)), motorKv*Values.batteryCells*3.7)
        rpm = throttle*maxRPM
        maxVe = maxRPM*0.0254*(Values.propPitch+0.5)/60
        Ve = rpm*0.0254*(Values.propPitch+0.5)/60
        force = a*(Ve**2)
        if inflowVelocity>=0:
            ic = max(0.2, (maxVe-inflowVelocity)/maxVe)
        else:
            ic = max(0.2, (maxVe+inflowVelocity)/maxVe)
        force*=ic
        if throttle < 0:
            force *= -1
        # FPV_Drone.console(throttle, a, ic, force, inflowVelocity, ic, rpm, maxRPM, mag(DroneState.velocity))
    else:
        force = throttle * motorKv/30
        # FPV_Drone.console(throttle, force)
    return force   
    
def startDrone(startPos):
    DroneState.position = [startPos[0], startPos[1], startPos[2]]
    DroneState.velocity = [0.01, 10, 0]
    ac.setCameraMode(6)
    ac.ext_setCameraFov(float(Values.cameraFov))
    AppState.toggleDrone = True

def dronePhysics(deltaT):
    airDragCoefficient = Values.airDrag/100
    droneSurfaceArea = Values.droneSurfaceArea*0.0001
    minimalSurfaceAreaCoefficient = Values.minimalSurfaceAreaCoefficient
    gravity = Values.gravity
    
    if ac.getCameraMode() != 6:
        DroneState.isAsleep = True
        return

    if DroneState.isAsleep: # just woke up
        DroneState.isAsleep = False
        ac.ext_setCameraFov(float(Values.cameraFov))

    ac.freeCameraRotatePitch(-math.radians(Values.cameraAngle))
    cameraMatrix = ac.ext_getCameraMatrix()
    upVector = [cameraMatrix[4], cameraMatrix[5], cameraMatrix[6]]
    thrustVector = upVector
    angle = math.acos(dot(thrustVector,DroneState.velocity)/(mag(thrustVector)*mag(DroneState.velocity)))
    inflowVelocity = mag(DroneState.velocity)*math.cos(angle)

    force = [
        -airDrag(Values.airDensity, DroneState.velocity[0], airDragCoefficient, droneSurfaceArea, minimalSurfaceAreaCoefficient, angle),
        -airDrag(Values.airDensity, DroneState.velocity[1], airDragCoefficient, droneSurfaceArea, minimalSurfaceAreaCoefficient, angle),
        -airDrag(Values.airDensity, DroneState.velocity[2], airDragCoefficient, droneSurfaceArea, minimalSurfaceAreaCoefficient, angle)
    ]

    acceleration = [
        (throttleForce(Values.motorKv, Input.throttle, inflowVelocity)*thrustVector[0] + force[0])/(Values.droneMass/1000),
        (throttleForce(Values.motorKv, Input.throttle, inflowVelocity)*thrustVector[1] + force[1])/(Values.droneMass/1000) - gravity,
        (throttleForce(Values.motorKv, Input.throttle, inflowVelocity)*thrustVector[2] + force[2])/(Values.droneMass/1000)
    ]

    DroneState.velocity[0] += acceleration[0] * deltaT
    DroneState.velocity[1] += acceleration[1] * deltaT
    DroneState.velocity[2] += acceleration[2] * deltaT

    DroneState.position[0] += DroneState.velocity[0]*deltaT
    DroneState.position[1] += DroneState.velocity[1]*deltaT
    DroneState.position[2] += DroneState.velocity[2]*deltaT

    if DroneState.position[1] < Values.groundLevel+0.1:
        DroneState.position[1] = Values.groundLevel+0.1
        DroneState.velocity[1] = 0

    ac.ext_setCameraPosition(tuple(DroneState.position))

    ac.freeCameraRotatePitch(math.radians(Input.pitch*-1)*deltaT)
    ac.freeCameraRotateHeading(math.radians(Input.yaw*-1)*deltaT)
    ac.freeCameraRotateRoll(math.radians(Input.roll*-1)*deltaT)
    ac.freeCameraRotatePitch(math.radians(Values.cameraAngle))
