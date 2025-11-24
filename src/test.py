"""Main entry point for power supply control examples."""

from devices.core.connection import create_connection, ConnectionType
from devices.psu import BK9130, BK9200


def test_bk9130():
    """Example usage of BK9130 power supply."""
    # Create a VISA USB TMC connection
    # Replace with your actual instrument address
    address = "USB0::0xFFFF::0x9130::802360043766810027::INSTR"  # Update with your device address
    
    # Create connection
    connection = create_connection(
        connection_type=ConnectionType.VISA,
        address=address,
        timeout=10.0
    )
    
    # Use the BK9130 power supply with context manager
    with BK9130(connection) as psu:
        # Identify the instrument
        print(f"Instrument ID: {psu.identify()}")
        
        # Configure Channel 1
        print("\nConfiguring Channel 1...")
        psu.set_voltage(1, 12.0)  # Set to 12V
        psu.set_current(1, 1.5)   # Set current limit to 1.5A
        print(f"Channel 1 - Voltage: {psu.get_voltage(1)}V, Current: {psu.get_current(1)}A")
        
        # Configure Channel 2
        print("\nConfiguring Channel 2...")
        psu.set_voltage(2, 5.0)   # Set to 5V
        psu.set_current(2, 2.0)   # Set current limit to 2.0A
        print(f"Channel 2 - Voltage: {psu.get_voltage(2)}V, Current: {psu.get_current(2)}A")
        
        # Configure Channel 3
        print("\nConfiguring Channel 3...")
        psu.set_voltage(3, 3.3)   # Set to 3.3V
        psu.set_current(3, 1.0)   # Set current limit to 1.0A
        print(f"Channel 3 - Voltage: {psu.get_voltage(3)}V, Current: {psu.get_current(3)}A")
        
        # Enable all outputs
        print("\nEnabling all outputs...")
        psu.set_all_outputs(True)
        
        # Wait a moment for outputs to stabilize
        import time
        time.sleep(10)
        
        # Measure actual values
        print("\nMeasured Values:")
        for ch in range(1, 4):
            voltage = psu.measure_voltage(ch)
            current = psu.measure_current(ch)
            output_state = psu.get_output(ch)
            print(f"Channel {ch}: {voltage:.3f}V, {current:.3f}A, Output: {'ON' if output_state else 'OFF'}")
        
        # Get comprehensive status
        print("\nFull Status:")
        status = psu.get_status()
        for channel, data in status.items():
            print(f"{channel}:")
            for key, value in data.items():
                print(f"  {key}: {value}")
        
        # Disable all outputs before exiting
        print("\nDisabling all outputs...")
        psu.set_all_outputs(False)
        
        print("\nDone!")


def test_bk9200():
    """Example usage of BK9200 power supply."""
    # Create a VISA USB TMC connection
    # Replace with your actual instrument address
    address = "USB0::0xFFFF::0x9200::802204020757710095::INSTR"  # Update with your BK9200 device address
    
    # Create connection
    connection = create_connection(
        connection_type=ConnectionType.VISA,
        address=address,
        timeout=10.0
    )
    
    # Use the BK9200 power supply with context manager
    # Note: Set num_channels based on your model (1 for single channel, 2 for dual channel)
    num_channels = 1  # Change to 2 if you have a dual-channel model
    with BK9200(connection, num_channels=num_channels) as psu:
        # Identify the instrument
        print(f"Instrument ID: {psu.identify()}")
        
        # Configure Channel 1
        print("\nConfiguring Channel 1...")
        psu.set_voltage(1, 12.0)  # Set to 12V
        psu.set_current(1, 2.0)   # Set current limit to 2.0A
        print(f"Channel 1 - Voltage: {psu.get_voltage(1)}V, Current: {psu.get_current(1)}A")
        
        # Set over-voltage protection (OVP)
        psu.set_ovp(1, 13.0)  # Set OVP to 13V
        print(f"Channel 1 - OVP: {psu.get_ovp(1)}V")
        
        # Set over-current protection (OCP)
        psu.set_ocp(1, 2.5)  # Set OCP to 2.5A
        print(f"Channel 1 - OCP: {psu.get_ocp(1)}A")
        
        # If multi-channel, configure Channel 2
        if num_channels > 1:
            print("\nConfiguring Channel 2...")
            psu.set_voltage(2, 5.0)   # Set to 5V
            psu.set_current(2, 1.5)   # Set current limit to 1.5A
            print(f"Channel 2 - Voltage: {psu.get_voltage(2)}V, Current: {psu.get_current(2)}A")
            psu.set_ovp(2, 6.0)
            psu.set_ocp(2, 2.0)
        
        # Enable output
        print("\nEnabling output...")
        psu.set_output(1, True)
        if num_channels > 1:
            psu.set_output(2, True)
        
        # Wait a moment for outputs to stabilize
        import time
        time.sleep(5)
        
        # Measure actual values
        print("\nMeasured Values:")
        for ch in range(1, num_channels + 1):
            voltage = psu.measure_voltage(ch)
            current = psu.measure_current(ch)
            output_state = psu.get_output(ch)
            print(f"Channel {ch}: {voltage:.3f}V, {current:.3f}A, Output: {'ON' if output_state else 'OFF'}")
        
        # Get comprehensive status
        print("\nFull Status:")
        status = psu.get_status()
        for channel, data in status.items():
            print(f"{channel}:")
            for key, value in data.items():
                print(f"  {key}: {value}")
        
        # Disable output before exiting
        print("\nDisabling output...")
        psu.set_output(1, False)
        if num_channels > 1:
            psu.set_output(2, False)
        
        print("\nDone!")


def main():
    test_bk9200()
    test_bk9130()


if __name__ == "__main__":
    main()

