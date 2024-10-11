from pyfirmata import Arduino, util
import time

# Define constants
SERVO_NUM = 5
PWM_MAX = 2000
PWM_MIN = 1000
ADC_MIN = 412
ADC_MAX = 612

# Define pin numbers
dwq_pins = [0, 1, 2, 3, 5]  # Replace with the actual pin numbers connected to sensors
servo_pins = [2, 3, 4, 5, 6]  # Replace with the actual servo pin numbers

# '/dev/ttyACM0'

# Initialize Arduino board
board = Arduino('COM8')  # Replace with the actual port of your Arduino

# Attach servo instances to corresponding pins
servos = [board.get_pin('d:{}:s'.format(pin)) for pin in servo_pins]

# Set up iterator for non-blocking communication
it = util.Iterator(board)
it.start()

# Main loop
try:
    while True:
        for i in range(SERVO_NUM):
           
            # Read analog input from sensor
            adc_value = board.analog[dwq_pins[i]].read()

            print(adc_value, 'adc_value')
            if adc_value is not None:
                # Map ADC value to servo range
                servo_value = int((adc_value - 0) * (PWM_MAX - PWM_MIN) / (1 - 0) + PWM_MIN)
                # Write servo value
                servos[i].write(servo_value)
                # Print servo value
                print(f"Servo {i}: {servo_value}")

        # Delay between iterations
        time.sleep(0.1)

except KeyboardInterrupt:
    # Release servo pins on Ctrl+C
    for servo in servos:
        servo.write(90)  # Center position
    board.exit()
