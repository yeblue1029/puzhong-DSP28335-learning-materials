/*
 * aic23.h
 *
 *  Created on: 2018年8月24日
 *      Author: Administrator
 */

#ifndef AIC23_H_
#define AIC23_H_


#include "DSP2833x_Device.h"     // DSP2833x 头文件
#include "DSP2833x_Examples.h"   // DSP2833x 例子相关头文件



void I2CA_Init(void);
Uint16 AIC23Write(int Address,int Data);



#endif /* APP_AIC23_AIC23_H_ */
