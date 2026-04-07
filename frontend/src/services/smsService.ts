export interface SMSLog {
  to: string;
  studentName: string;
  message: string;
  status: 'sent' | 'failed';
  timestamp: string;
}

/**
 * Mock SMS Service
 * In a production environment, this would integrate with Twilio, Nexmo, or Fast2SMS.
 * For this demonstration, it logs the SMS to the console and saves it to localStorage.
 */
export const smsService = {
  sendSMS: async (phone: string, studentName: string, message: string): Promise<boolean> => {
    if (!phone) {
      console.warn(`[SMS Service] Failed to send to ${studentName} - No phone number.`);
      return false;
    }

    console.log(`📱 [SMS INITIATED to ${studentName} (${phone})]: ${message}`);

    try {
      const BACKEND = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const response = await fetch(`${BACKEND}/api/v1/sms/send`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ to: phone, message }),
      });

      if (!response.ok) {
        const errortext = await response.text();
        throw new Error(`Backend error: ${response.status} ${errortext}`);
      }

      console.log(`✅ [SMS SUCCESS to ${studentName} (${phone})]`);

      // Log to history
      const logs: SMSLog[] = JSON.parse(localStorage.getItem('smsLogs') || '[]');
      logs.push({
        to: phone,
        studentName,
        message,
        status: 'sent',
        timestamp: new Date().toISOString()
      });
      localStorage.setItem('smsLogs', JSON.stringify(logs));

      return true;
    } catch (error) {
      console.error(`❌ [SMS FAILED to ${studentName} (${phone})]:`, error);

      // Log failure
      const logs: SMSLog[] = JSON.parse(localStorage.getItem('smsLogs') || '[]');
      logs.push({
        to: phone,
        studentName,
        message,
        status: 'failed',
        timestamp: new Date().toISOString()
      });
      localStorage.setItem('smsLogs', JSON.stringify(logs));

      return false;
    }
  },
  
  /**
   * Automatically sends attendance notifications to all students in the final attendance record
   */
  sendBatchAttendanceSMS: async (classId: string, finalAttendance: any[], allStudents: any[]) => {
    console.log(`📢 Sending attendance SMS notifications for class ${classId}...`);
    let sentCount = 0;
    
    for (const record of finalAttendance) {
      const student = allStudents.find((s: any) => s.student_id === record.student_id);
      
      if (student && student.phone) {
        const isPresent = record.status === 'present';
        const date = new Date().toLocaleDateString();
        
        const message = isPresent 
          ? `Smart Attendance: Dear ${student.name}, you have been marked PRESENT for class ${classId} on ${date}.`
          : `Smart Attendance: Dear ${student.name}, you have been marked ABSENT for class ${classId} on ${date}.`;
          
        await smsService.sendSMS(student.phone, student.name, message);
        sentCount++;
      }
    }
    
    console.log(`✅ Completed sending ${sentCount} SMS notifications.`);
  }
};
