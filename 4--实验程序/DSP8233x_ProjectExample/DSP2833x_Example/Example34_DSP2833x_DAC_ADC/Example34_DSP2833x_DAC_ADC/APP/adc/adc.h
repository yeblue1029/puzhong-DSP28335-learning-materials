/*
 * adc.h
 *
 *  Created on: 2018-1-29
 *      Author: Administrator
 */

#ifndef ADC_H_
#define ADC_H_

#include "DSP2833x_Device.h"     // DSP2833x 头文件
#include "DSP2833x_Examples.h"   // DSP2833x 例子相关头文件



void ADC_Init(void);
Uint16 Read_ADCValue(void);

#endif /* ADC_H_ */
