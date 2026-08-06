/*
 * beep.h
 *
 *  Created on: 2018-1-20
 *      Author: Administrator
 */

#ifndef BEEP_H_
#define BEEP_H_


#include "DSP2833x_Device.h"     // DSP2833x 头文件
#include "DSP2833x_Examples.h"   // DSP2833x 例子相关头文件


#define BEEP_ON			(GpioDataRegs.GPASET.bit.GPIO6=1)
#define BEEP_OFF		(GpioDataRegs.GPACLEAR.bit.GPIO6=1)
#define BEEP_TOGGLE		(GpioDataRegs.GPATOGGLE.bit.GPIO6=1)

void BEEP_Init(void);

#endif /* BEEP_H_ */
