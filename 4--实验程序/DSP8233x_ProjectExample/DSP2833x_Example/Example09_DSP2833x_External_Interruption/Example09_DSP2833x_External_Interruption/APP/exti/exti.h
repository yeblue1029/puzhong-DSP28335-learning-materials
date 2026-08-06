/*
 * exti.h
 *
 *  Created on: 2018-1-25
 *      Author: Administrator
 */

#ifndef EXTI_H_
#define EXTI_H_


#include "DSP2833x_Device.h"     // DSP2833x 头文件
#include "DSP2833x_Examples.h"   // DSP2833x 例子相关头文件


void EXTI1_Init(void);
interrupt void EXTI1_IRQn(void);

void EXTI2_Init(void);
interrupt void EXTI2_IRQn(void);

#endif /* EXTI_H_ */
