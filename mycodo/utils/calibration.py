# coding=utf-8
import logging
import time

logger = logging.getLogger("mycodo.atlas_scientific")

if logging.getLevelName(logging.getLogger().getEffectiveLevel()) == 'INFO':
    logger.setLevel(logging.INFO)


class AtlasScientificCommand:
    """
    Class to handle issuing commands to the Atlas Scientific sensor boards
    """

    def __init__(self, input_dev, sensor=None):
        self.cmd_send = None
        self.ph_sensor_uart = None
        self.ph_sensor_i2c = None
        self.interface = input_dev.interface
        self.init_error = None

        if sensor:
            self.atlas_device = sensor
        elif self.interface == 'FTDI':
            from mycodo.devices.atlas_scientific_ftdi import AtlasScientificFTDI
            self.atlas_device = AtlasScientificFTDI(
                input_dev.ftdi_location)
        elif self.interface == 'UART':
            from mycodo.devices.atlas_scientific_uart import AtlasScientificUART
            self.atlas_device = AtlasScientificUART(
                input_dev.uart_location,
                baudrate=input_dev.baud_rate)
        elif self.interface == 'I2C':
            from mycodo.devices.atlas_scientific_i2c import AtlasScientificI2C
            self.atlas_device = AtlasScientificI2C(
                i2c_address=int(str(input_dev.i2c_location), 16),
                i2c_bus=input_dev.i2c_bus)

        (self.measurement,
         self.board_version,
         self.firmware_version) = self.atlas_device.get_board_version()

        if self.board_version == 0:
            error_msg = "Atlas Scientific board initialization unsuccessful. " \
                        "Unable to retrieve device info (this indicates the " \
                        "device was not properly initialized or connected). " \
                        "Returned: {}, {}, {}".format(
                 self.measurement,
                 self.board_version,
                 self.firmware_version)
            logger.error(error_msg)
            self.init_error = error_msg
        else:
            logger.debug(
                "Atlas Scientific board initialization success. "
                "Measurement: {meas}, Board: {brd}, Firmware: {fw}".format(
                    meas=self.measurement,
                    brd=self.board_version,
                    fw=self.firmware_version))

    def get_sensor_measurement(self):
        return self.measurement

    def calibrate(self, command, set_amount=None, custom_cmd=None):
        """
        Determine and send the correct command to an Atlas Scientific sensor,
        based on the board version
        """
        # Formulate command based on calibration step and board version.
        # Legacy boards requires a different command than recent boards.
        # Some commands are not necessary for recent boards and will not
        # generate a response.
        err = 1
        msg = "Default message"

        if self.init_error:
            msg = self.init_error

        # Atlas EC
        if command == 'ec_dry':
            if self.board_version == 2:
                err, msg = self.send_command('cal,dry')
        elif command == 'ec_low':
            if self.board_version == 2:
                err, msg = self.send_command('cal,low,{uS}'.format(uS=set_amount))
        elif command == 'ec_high':
            if self.board_version == 2:
                err, msg = self.send_command('cal,high,{uS}'.format(uS=set_amount))

        # Atlas pH
        elif command == 'temperature' and set_amount is not None:
            if self.board_version == 1:
                err, msg = self.send_command(set_amount)
            elif self.board_version == 2:
                err, msg = self.send_command('T,{temp}'.format(temp=set_amount))
        elif command == 'clear_calibration':
            if self.board_version == 1:
                err, msg = self.send_command('X')
                self.send_command('L0')
            elif self.board_version == 2:
                err, msg = self.send_command('Cal,clear')
        elif command == 'continuous':
            if self.board_version == 1:
                err, msg = self.send_command('C')
            elif self.board_version == 2:
                err, msg = self.send_command('C,1')
        elif command == 'low':
            if self.board_version == 1:
                err, msg = self.send_command('F')
            elif self.board_version == 2:
                err, msg = self.send_command('Cal,low,4.00')
        elif command == 'mid':
            if self.board_version == 1:
                err, msg = self.send_command('S')
            elif self.board_version == 2:
                err, msg = self.send_command('Cal,mid,7.00')
        elif command == 'high':
            if self.board_version == 1:
                err, msg = self.send_command('T')
            elif self.board_version == 2:
                err, msg = self.send_command('Cal,high,10.00')
        elif command == 'calibrated':  # Not implemented. This queries whether there is a stored calibration
            if self.board_version == 1:
                err = 'success'
                msg = 'Calibrated query not implemented on board version 1 (assume it was successfully calibrated)'
            elif self.board_version == 2:
                err, msg = self.send_command('Cal,?')
        elif command == 'end':
            if self.board_version == 1:
                err, msg = self.send_command('E')
            elif self.board_version == 2:
                err, msg = self.send_command('C,0')
        elif custom_cmd:
            err, msg = self.send_command(custom_cmd)

        return err, msg

    def send_command(self, cmd_send):
        """ Send the command (if not None) and return the response """
        try:
            return_value = "No message"
            if cmd_send is not None:
                if self.interface == 'FTDI':
                    return_value = self.ph_sensor_ftdi.query(cmd_send)
                elif self.interface == 'UART':
                    return_value = self.ph_sensor_uart.query(cmd_send)
                elif self.interface == 'I2C':
                    return_value = self.ph_sensor_i2c.query(cmd_send)
                time.sleep(0.1)
                return 0, return_value
            else:
                return 1, "No command given"
        except Exception as err:
            logger.error("{cls} raised an exception while communicating with "
                         "the board: {err}".format(cls=type(self).__name__,
                                                   err=err))
            return 1, err
