/////////////////////////////////////
#include	"DSP2833x_Device.h"

FLAGS bFlags;
extern unsigned char DBUF[BUFFER_LENGTH];
unsigned char usector;
extern unsigned long  DirStartCluster32;		
extern unsigned long  DirStartCluster;
extern SYS_INFO_BLOCK   DeviceInfo;
unsigned char DataBuf[BUFFER_LENGTH];
extern	FILE_INFO   	 ThisFile;

/////////////////////////////////////////////////
void play_Udisc();

void play_Udisc()
{
    int temp,i;

 
    DirStartCluster=0;
	DirStartCluster32=0;

	for(temp=0;temp<512;temp++)
		DBUF[temp]=0;


	
	
		   		DirStartCluster=0;
				DirStartCluster32=0;
				ThisFile.FatSectorPointer=0;
				DeviceInfo.LastFreeCluster=0;

			if(InitFileSystem())
				{
				bFlags.bits.SLAVE_IS_ATTACHED = TRUE;				
			
				}
			else
				{				
				bFlags.bits.SLAVE_IS_ATTACHED = FALSE;				
				}		
				
			
		

		if(bFlags.bits.SLAVE_IS_ATTACHED)
			{
				CreateFile("demo123.txt",0x20);
				for (i=0;i<100;i++)
				{
		     		DataBuf[i*10+0]='U';
		     		DataBuf[i*10+1]=' ';
		     		DataBuf[i*10+2]='D';
		     		DataBuf[i*10+3]='I';
		     		DataBuf[i*10+4]='S';
		     		DataBuf[i*10+5]='K';
					DataBuf[i*10+6]=' ';
					DataBuf[i*10+7]='!';
					DataBuf[i*10+8]= 13;
					DataBuf[i*10+9]= 10; 
				}		     	     
				for(i=0;i<10;i++)
				{
					SetFilePointer(ThisFile.LengthInByte);
					WriteFile(1000,DataBuf);
				
				}
						   asm ("      ESTOP0");//ok	
			}		
		
		asm ("      ESTOP0");//error  
    	
}
