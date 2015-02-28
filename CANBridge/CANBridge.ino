#include <Canbus.h>

unsigned char raw_buffer[13];
unsigned char buffer[8];  // Buffer to store the incoming data
unsigned char serial_input_buffer[12];
int serial_input_buffer_i=0;

void setup() {
  Serial.begin(115200);
  delay(1000);
  
  if(Canbus.init(CANSPEED_500))  /* Initialise MCP2515 CAN controller at the specified speed */
    Serial.println("CAN Init ok");
  else
    Serial.println("Can't init CAN");
    
  delay(1000);
}

void loop() {
  uint16_t id;
  int8_t rtr;
  uint8_t length;
  
  if(Canbus.raw_message_rx(id, rtr, length, raw_buffer, buffer)) // Check to see if we have a message on the Bus
  {
    char str_buffer[100];
    
    sprintf(str_buffer,"CAN Message: [%2x] %d %.2x %.2x %.2x %.2x %.2x %.2x %.2x %.2x", id, length, buffer[0], buffer[1], buffer[2], buffer[3], buffer[4], buffer[5], buffer[6], buffer[7] );
    Serial.println(str_buffer);
  }
  
  if (Serial.available() > 0) {
    int byte = Serial.read();

    Serial.print("Received: ");
    Serial.println(byte, DEC);
    
    serial_input_buffer[serial_input_buffer_i++]=byte;
    
    if(serial_input_buffer_i==12)
    {
      serial_input_buffer_i=0;
      unsigned char message[8];
      Canbus.message_tx(*((int *)serial_input_buffer),serial_input_buffer+4);
    }
  }
}
