/*
 * main.c
 *
 *  Created on: 2018-3-21
 *      Author: Administrator
 */

//    This program requires the DSP2833x header files.
//
//    Test requires the following hardware connections from EPWM1 and
//    GPIO pins (simulating QEP sensor) to QEP peripheral
//
//       GPIO50/EQEP1A <- GPIO0/EPWM1A (simulates EQEP Phase A signal)
//       GPIO51/EQEP1B <- GPIO1/EPWM1B (simulates EQEP Phase B signal)
//       GPIO53/EQEP1I <- GPIO4 (simulates EQEP Index Signal)
//
// DESCRIPTION:
//
//    This test will provide position measurement,  speed measurement using the capture unit, and
//    speed measurement using unit time out. This example uses the IQMath library. It is used
//    merely to simplify high-precision calculations.
//
//    See DESCRIPTION in Example_posspeed.c for more details on the calculations
//    performed in this example.
//
//    In addition to this file, the following files must be included in this project:
//    Example_posspeed.c - includes all eQEP functions
//    Example_EPwmSetup.c - sets up EPWM1A and EPWM1B as simulated QA and QB encoder signals
//    Example_posspeed.h - includes initialization values for pos and speed structure
//
//    Notes:
//    * Maximum speed is configured to 6000rpm(BaseRpm)
//    * Minimum speed is assumed at 10rpm for capture pre-scalar selection
//    * Pole pair is configured to 2 (pole_pairs)
//    * QEP Encoder resolution is configured to 4000counts/revolution (mech_scaler)
//      which means: 4000/4 = 1000 line/revolution quadrature encoder (simulated by EPWM1)
//    * EPWM1 (simulating QEP encoder signals) is configured for 5kHz frequency or 300 rpm
//      (=4*5000 cnts/sec * 60 sec/min)/4000 cnts/rev)
//    * 300 rpm EPWM1 speed will be measured by EQEP.
//
// 	  SPEEDRPM_FR: High Speed Measurement is obtained by counting the QEP input pulses
//              for 10ms (unit timer set to 100Hz).
//
//    SPEEDRPM_FR = { (Position Delta)/10ms } * 60 rpm
//
//
//    SPEEDRPM_PR: Low Speed Measurement is obtained by measuring time period of QEP edges.
//              Time measurement is averaged over 64edges for better results and
//              capture unit performs the time measurement using pre-scaled SYSCLK
//
//              Note that pre-scaler for capture unit clock is selected such that
//              capture timer does not overflow at the required minimum RPM speed
//
//          Watch Variables: qep_posspeed.SpeedRpm_fr - Speed meas. in rpm using QEP position counter
//                           qep_posspeed.SpeedRpm_pr - Speed meas. in rpm using capture unit
//                           qep_posspeed.theta_mech - Motor mechanical angle (Q15)
//                           qep_posspeed.theta_elec - Motor electrical angle (Q15)
//

#include "DSP2833x_Device.h"     // DSP2833x Headerfile Include File
#include "DSP2833x_Examples.h"   // DSP2833x Examples Include File

#include "leds.h"
#include "time.h"
#include "uart.h"
#include "stdio.h"
#include "eqep.h"




/*******************************************************************************
* 函 数 名         : main
* 函数功能		   : 主函数
* 输    入         : 无
* 输    出         : 无
*******************************************************************************/
void main()
{
	Uint16 i=0;


	InitSysCtrl();
	InitPieCtrl();
	IER = 0x0000;
	IFR = 0x0000;
	InitPieVectTable();

	LED_Init();
	TIM0_Init(150,200000);//200ms
	UARTa_Init(4800);

	EQEP1_Init();

	while(1)
	{

	}
}

