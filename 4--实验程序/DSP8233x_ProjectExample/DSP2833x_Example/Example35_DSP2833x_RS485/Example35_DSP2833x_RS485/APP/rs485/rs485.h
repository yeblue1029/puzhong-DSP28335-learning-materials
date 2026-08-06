/*
 * rs485.h
 *
 *  Created on: 2018-4-21
 *      Author: Administrator
 */

#ifndef RS485_H_
#define RS485_H_

#include "DSP2833x_Device.h"     // DSP2833x 头文件
#include "DSP2833x_Examples.h"   // DSP2833x 例子相关头文件


#define RS485_DIR_SETH		(GpioDataRegs.GPBSET.bit.GPIO61=1)
#define RS485_DIR_SETL		(GpioDataRegs.GPBCLEAR.bit.GPIO61=1)
//#define RS485_DIR_SETH		(GpioDataRegs.GPBSET.bit.GPIO34=1)
//#define RS485_DIR_SETL		(GpioDataRegs.GPBCLEAR.bit.GPIO34=1)

void RS485_Init(Uint32 bound);
void RS485_SendByte(int a);
void RS485_SendString(char * msg);


#endif /* RS485_H_ */
