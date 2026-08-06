/*
 * tlv5620.h
 *
 *  Created on: 2018-3-1
 *      Author: Administrator
 */

#ifndef TLV5620_H_
#define TLV5620_H_


#include "DSP2833x_Device.h"     // DSP2833x Headerfile Include File
#include "DSP2833x_Examples.h"   // DSP2833x Examples Include File


#define SET_LOAD 	(GpioDataRegs.GPASET.bit.GPIO26=1)
#define ClEAR_LOAD 	(GpioDataRegs.GPACLEAR.bit.GPIO26=1)


void TLV5620_Init(void);
void DAC_SetChannelData(unsigned char channel,unsigned char rng,unsigned char dat);

#endif /* TLV5620_H_ */
