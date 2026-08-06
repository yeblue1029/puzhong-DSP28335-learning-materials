/*
 * step_motor.h
 *
 *  Created on: 2018-1-23
 *      Author: Administrator
 */

#ifndef STEP_MOTOR_H_
#define STEP_MOTOR_H_

#include "DSP2833x_Device.h"     // DSP2833x 头文件
#include "DSP2833x_Examples.h"   // DSP2833x 例子相关头文件

#define STEP_MOTOR_4LINE2
//#define STEP_MOTOR_5LINE4


#define MOTO_OUTA_SETH	(GpioDataRegs.GPASET.bit.GPIO2=1)
#define MOTO_OUTA_SETL	(GpioDataRegs.GPACLEAR.bit.GPIO2=1)

#define MOTO_OUTB_SETH	(GpioDataRegs.GPASET.bit.GPIO3=1)
#define MOTO_OUTB_SETL	(GpioDataRegs.GPACLEAR.bit.GPIO3=1)

#define MOTO_OUTC_SETH	(GpioDataRegs.GPASET.bit.GPIO4=1)
#define MOTO_OUTC_SETL	(GpioDataRegs.GPACLEAR.bit.GPIO4=1)

#define MOTO_OUTD_SETH	(GpioDataRegs.GPASET.bit.GPIO5=1)
#define MOTO_OUTD_SETL	(GpioDataRegs.GPACLEAR.bit.GPIO5=1)

void Step_Motor_Init(void);


#endif /* STEP_MOTOR_H_ */
