/*
 * aic23.c
 *
 *  Created on: 2018年8月24日
 *      Author: Administrator
 */

#include "aic23.h"
#include "key.h"



void Delay(int time)
{
	int i,j,k=0;
	for(i=0;i<time;i++)
		for(j=0;j<1024;j++)
			k++;
}

void Mydelay(Uint32 k)
{
	while(k--);
}

void I2CA_Init(void)
{
   // Initialize I2C
   I2caRegs.I2CSAR = 0x001A;		// Slave address - EEPROM control code

   #if (CPU_FRQ_150MHZ)             // Default - For 150MHz SYSCLKOUT
        I2caRegs.I2CPSC.all = 14;   // Prescaler - need 7-12 Mhz on module clk (150/15 = 10MHz)
   #endif
   #if (CPU_FRQ_100MHZ)             // For 100 MHz SYSCLKOUT
     I2caRegs.I2CPSC.all = 9;	    // Prescaler - need 7-12 Mhz on module clk (100/10 = 10MHz)
   #endif

   I2caRegs.I2CCLKL = 100;			// NOTE: must be non zero
   I2caRegs.I2CCLKH = 100;			// NOTE: must be non zero
   I2caRegs.I2CIER.all = 0x24;		// Enable SCD & ARDY interrupts

//   I2caRegs.I2CMDR.all = 0x0020;	// Take I2C out of reset
   I2caRegs.I2CMDR.all = 0x0420;	// Take I2C out of reset		//zq
   									// Stop I2C when suspended

   I2caRegs.I2CFFTX.all = 0x6000;	// Enable FIFO mode and TXFIFO
   I2caRegs.I2CFFRX.all = 0x2040;	// Enable RXFIFO, clear RXFFINT,

   return;
}

Uint16 AIC23Write(int Address,int Data)
{


   if (I2caRegs.I2CMDR.bit.STP == 1)
   {
      return I2C_STP_NOT_READY_ERROR;
   }

   // Setup slave address
   I2caRegs.I2CSAR = 0x1A;

   // Check if bus busy
   if (I2caRegs.I2CSTR.bit.BB == 1)
   {
      return I2C_BUS_BUSY_ERROR;
   }

   // Setup number of bytes to send
   // MsgBuffer + Address
   I2caRegs.I2CCNT = 2;
   I2caRegs.I2CDXR = Address;
   I2caRegs.I2CDXR = Data;
   // Send start as master transmitter
   I2caRegs.I2CMDR.all = 0x6E20;
   return I2C_SUCCESS;

}




extern char KEYValue;

void AIC23_Test(void)
{
	Uint16 temp,i;
	int y;

	InitMcbspaGpio();	//zq
	InitI2CGpio();

	I2CA_Init();

	AIC23Write(0x00,0x00);
	Delay(100);
	AIC23Write(0x02,0x00);
	Delay(100);
	AIC23Write(0x04,0x7f);
	Delay(100);
	AIC23Write(0x06,0x7f);
	Delay(100);
	AIC23Write(0x08,0x14);
	Delay(100);
	AIC23Write(0x0A,0x00);
	Delay(100);
	AIC23Write(0x0C,0x00);
	Delay(100);
	AIC23Write(0x0E,0x43);
	Delay(100);
	AIC23Write(0x10,0x23);
	Delay(100);
	AIC23Write(0x12,0x01);
	Delay(100);		//AIC23Init

	InitMcbspa();          // Initalize the Mcbsp-A

	while(1)
	{
		for(temp=30000;temp>0;temp-=100)
		{
			for(i=0;i<2;i++)
			{
				y=5000;
				Mydelay(temp);
				McbspaRegs.DXR1.all = y;// 输出左声道数据
				McbspaRegs.DXR2.all = y;// 输出右声道数据
				y=-5000;
				Mydelay(temp);
				McbspaRegs.DXR1.all = y;// 输出左声道数据
				McbspaRegs.DXR2.all = y;// 输出右声道数据
			}
			if(KEYValue!=KEY6_PRESS)
			{

				return;
			}
		}

		if(KEYValue!=KEY6_PRESS)
		{

			return;
		}
	}
}

