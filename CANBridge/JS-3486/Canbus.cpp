/**
 * 
 *
 * Copyright (c) 2008-2009  All rights reserved.
 */

#if ARDUINO>=100
#include <Arduino.h> // Arduino 1.0
#else
#include <Wprogram.h> // Arduino 0022
#endif
#include <stdint.h>
#include <avr/pgmspace.h>

#include <stdio.h>
#include <avr/io.h>
#include <avr/interrupt.h>
#include <util/delay.h>
#include "pins_arduino.h"
#include <inttypes.h>
#include "global.h"
#include "mcp2515.h"
#include "defaults.h"
#include "Canbus.h"




/* C++ wrapper */
CanbusClass::CanbusClass() {

 
}
unsigned int CanbusClass::message_rx(unsigned char *buffer) {
		tCAN message;
	
		if (mcp2515_check_message()) {
		
			
			// Read the message from the buffer the MCP2515
			if (mcp2515_get_message(&message)) {
				buffer[0] = message.data[0];
				buffer[1] = message.data[1];
				buffer[2] = message.data[2];
				buffer[3] = message.data[3];
				buffer[4] = message.data[4];
				buffer[5] = message.data[5];
				buffer[6] = message.data[6];
				buffer[7] = message.data[7];	
                return message.id;	
                //Serial.println("Got Something");																											
			}
			else {
			    //Serial.println("Can not read the message");
			}
		}
		return 0;
}

char CanbusClass::message_tx(unsigned int ID, unsigned char *buffer) {
	tCAN message;

	message.id = ID;
	message.header.rtr = 0;
	message.header.length = 8;
	message.data[0] = buffer[0];
	message.data[1] = buffer[1];
	message.data[2] = buffer[2];
	message.data[3] = buffer[3];
	message.data[4] = buffer[4];
	message.data[5] = buffer[5];
	message.data[6] = buffer[6];
	message.data[7] = buffer[7];						
	
	mcp2515_bit_modify(CANCTRL, (1<<REQOP2)|(1<<REQOP1)|(1<<REQOP0), 0);
		
	if (mcp2515_send_message(&message)) {
		return 1;
	
	}
	else {
		return 0;
	}
return 1;
 
}

char CanbusClass::ecu_req(unsigned char pid,  char *buffer) 
{
	tCAN message;
	float engine_data;
	int timeout = 0;
	char message_ok = 0;
	// Prepair message
	message.id = PID_REQUEST;
	message.header.rtr = 0;
	message.header.length = 8;
	message.data[0] = 0x02;
	message.data[1] = 0x01;
	message.data[2] = pid;
	message.data[3] = 0x00;
	message.data[4] = 0x00;
	message.data[5] = 0x00;
	message.data[6] = 0x00;
	message.data[7] = 0x00;						
	

	mcp2515_bit_modify(CANCTRL, (1<<REQOP2)|(1<<REQOP1)|(1<<REQOP0), 0);

	if (mcp2515_send_message(&message)) {
	}
	
	while(timeout < 4000)
	{
		timeout++;
				if (mcp2515_check_message()) 
				{

					if (mcp2515_get_message(&message)) 
					{
							if((message.id == PID_REPLY) && (message.data[2] == pid))	// Check message is the reply and its the right PID
							{
								switch(message.data[2])
								{   /* Details from http://en.wikipedia.org/wiki/OBD-II_PIDs */
									case ENGINE_RPM:  			//   ((A*256)+B)/4    [RPM]
									engine_data =  ((message.data[3]*256) + message.data[4])/4;
									sprintf(buffer,"%d rpm ",(int) engine_data);
									break;
							
									case ENGINE_COOLANT_TEMP: 	// 	A-40			  [degree C]
									engine_data =  message.data[3] - 40;
									sprintf(buffer,"%d degC",(int) engine_data);
							
									break;
							
									case VEHICLE_SPEED: 		// A				  [km]
									engine_data =  message.data[3];
									sprintf(buffer,"%d km ",(int) engine_data);
							
									break;

									case MAF_SENSOR:   			// ((256*A)+B) / 100  [g/s]
									engine_data =  ((message.data[3]*256) + message.data[4])/100;
									sprintf(buffer,"%d g/s",(int) engine_data);
							
									break;

									case O2_VOLTAGE:    		// A * 0.005   (B-128) * 100/128 (if B==0xFF, sensor is not used in trim calc)
									engine_data = message.data[3]*0.005;
									sprintf(buffer,"%d v",(int) engine_data);
							
									case THROTTLE:				// Throttle Position
									engine_data = (message.data[3]*100)/255;
									sprintf(buffer,"%d %% ",(int) engine_data);
									break;
							
								}
								message_ok = 1;
							}

					}
				}
				if(message_ok == 1) return 1;
	}


 	return 0;
}






char CanbusClass::init(unsigned char speed) {

  return mcp2515_init(speed);
 
}

CanbusClass Canbus;
