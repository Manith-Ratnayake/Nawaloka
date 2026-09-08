from datetime import time
from decimal import Decimal
from sqlalchemy.orm import Session
from core.clients import get_database_engine
from database.schema import Base, ChannelingSession, Doctor, HealthPackage, LabTest, Specialty


SPECIALTIES = [
    Specialty(id=1, name="General Surgery & Gastroenterology", department="Surgical Sciences"),
    Specialty(id=2, name="Neurosurgery", department="Neurosciences"),
    Specialty(id=3, name="ENT Surgery", department="Otorhinolaryngology"),
    Specialty(id=4, name="General Medicine", department="Internal Medicine"),
    Specialty(id=5, name="Respiratory & Chest Medicine", department="Pulmonology"),
    Specialty(id=6, name="Paediatrics", department="Paediatric Care"),
    Specialty(id=7, name="Cardiology", department="Heart Centre"),
    Specialty(id=8, name="Radiology & Imaging", department="Diagnostics"),
    Specialty(id=9, name="Cardiac Anaesthesia & Critical Care", department="Anaesthesiology"),
    Specialty(id=10, name="Rheumatology & Sports Medicine", department="Orthopaedics & Rehab"),
]

DOCTORS = [
    Doctor(id=1, name="Dr. Maiya Gunasekara", specialty_id=1, qualifications="MS, FRCS (Eng), Laparoscopic & Gastro Specialist", consultation_fee=Decimal("3500.00")),
    Doctor(id=2, name="Dr. Punsith Gunawardena", specialty_id=2, qualifications="MS, FRCS (Neuro), Consultant Neurosurgeon", consultation_fee=Decimal("4500.00")),
    Doctor(id=3, name="Dr. M.T.D Lakshan", specialty_id=3, qualifications="MS (ENT), DLO, Consultant ENT Surgeon", consultation_fee=Decimal("3000.00")),
    Doctor(id=4, name="Dr. Chandima De Mel", specialty_id=4, qualifications="MD, MRCP (UK), Consultant Physician", consultation_fee=Decimal("2800.00")),
    Doctor(id=5, name="Dr. Riaz Moujood", specialty_id=5, qualifications="MD, FCCP, Consultant Chest Specialist", consultation_fee=Decimal("3200.00")),
    Doctor(id=6, name="Dr. Duminda Pathirana", specialty_id=6, qualifications="MD, DCH, Consultant Paediatrician", consultation_fee=Decimal("2500.00")),
    Doctor(id=7, name="Dr. Prakash Priyadarshan", specialty_id=7, qualifications="MD, DM (Cardiology), Consultant Cardiologist", consultation_fee=Decimal("4000.00")),
    Doctor(id=8, name="Dr. Usha Samarasinghe", specialty_id=8, qualifications="MD (Radiology), Consultant Radiologist", consultation_fee=Decimal("2500.00")),
    Doctor(id=9, name="Dr. Sandeep K. Sharma", specialty_id=9, qualifications="MD, DA, Consultant Cardiac Intensivist", consultation_fee=Decimal("3800.00")),
    Doctor(id=10, name="Prof. Arjuna De Silva", specialty_id=4, qualifications="MD, FRCP (Lon), Senior Consultant Physician", consultation_fee=Decimal("4200.00")),
    Doctor(id=11, name="Dr. Harindu Wijesinghe", specialty_id=10, qualifications="MD, MRCP (UK), Consultant Rheumatologist", consultation_fee=Decimal("3500.00")),
]


CHANNELING_SESSIONS = [
    ChannelingSession(id=1, doctor_id=1, day_of_week="Monday", start_time=time(16, 0), end_time=time(18, 0), room_number="Room 102", max_patients=15),
    ChannelingSession(id=2, doctor_id=1, day_of_week="Wednesday", start_time=time(16, 0), end_time=time(18, 0), room_number="Room 102", max_patients=15),
    ChannelingSession(id=3, doctor_id=2, day_of_week="Tuesday", start_time=time(17, 0), end_time=time(19, 30), room_number="Room 205", max_patients=10),
    ChannelingSession(id=4, doctor_id=2, day_of_week="Saturday", start_time=time(9, 0), end_time=time(12, 0), room_number="Room 205", max_patients=15),
    ChannelingSession(id=5, doctor_id=3, day_of_week="Monday", start_time=time(8, 30), end_time=time(11, 0), room_number="Room 114", max_patients=20),
    ChannelingSession(id=6, doctor_id=3, day_of_week="Thursday", start_time=time(15, 0), end_time=time(17, 30), room_number="Room 114", max_patients=20),
    ChannelingSession(id=7, doctor_id=4, day_of_week="Tuesday", start_time=time(9, 0), end_time=time(12, 0), room_number="Room 108", max_patients=25),
    ChannelingSession(id=8, doctor_id=4, day_of_week="Friday", start_time=time(14, 0), end_time=time(17, 0), room_number="Room 108", max_patients=25),
    ChannelingSession(id=9, doctor_id=5, day_of_week="Wednesday", start_time=time(10, 0), end_time=time(12, 30), room_number="Room 210", max_patients=15),
    ChannelingSession(id=10, doctor_id=5, day_of_week="Saturday", start_time=time(14, 0), end_time=time(16, 30), room_number="Room 210", max_patients=15),
    ChannelingSession(id=11, doctor_id=6, day_of_week="Daily", start_time=time(16, 30), end_time=time(19, 0), room_number="Room 004 (Paediatric Wing)", max_patients=20),
    ChannelingSession(id=12, doctor_id=7, day_of_week="Monday", start_time=time(14, 0), end_time=time(17, 0), room_number="Heart Centre - Room 01", max_patients=12),
    ChannelingSession(id=13, doctor_id=7, day_of_week="Thursday", start_time=time(9, 0), end_time=time(12, 0), room_number="Heart Centre - Room 01", max_patients=12),
    ChannelingSession(id=14, doctor_id=10, day_of_week="Sunday", start_time=time(9, 0), end_time=time(12, 0), room_number="Room 301", max_patients=18),
    ChannelingSession(id=15, doctor_id=11, day_of_week="Friday", start_time=time(16, 0), end_time=time(18, 30), room_number="Room 112", max_patients=15),
]


LAB_TESTS = [
    LabTest(id=9, test_code="LAB-PPBS", test_name="Post Prandial Blood Sugar (PPBS)", category="Biochemistry", price=Decimal("650.00"), fasting_required_hours=0, preparation_instructions="Test must be taken exactly 2 hours after a standard meal.", report_delivery_hours=4),
    LabTest(id=10, test_code="LAB-OGTT", test_name="Oral Glucose Tolerance Test (OGTT)", category="Biochemistry", price=Decimal("1800.00"), fasting_required_hours=10, preparation_instructions="Requires 10-hour fasting. Multiple blood draws taken over 2 hours post 75g glucose drink.", report_delivery_hours=6),
    LabTest(id=11, test_code="LAB-UFR", test_name="Urine Full Report (UFR)", category="Clinical Pathology", price=Decimal("750.00"), fasting_required_hours=0, preparation_instructions="Collect mid-stream urine in a sterile container provided by the lab.", report_delivery_hours=3),
    LabTest(id=12, test_code="LAB-SFR", test_name="Stool Full Report & Occult Blood", category="Clinical Pathology", price=Decimal("850.00"), fasting_required_hours=0, preparation_instructions="Avoid red meat, turnips, and horseradish 48 hours prior to test.", report_delivery_hours=4),
    LabTest(id=13, test_code="LAB-ELECT", test_name="Serum Electrolytes (Na, K, Cl)", category="Biochemistry", price=Decimal("2400.00"), fasting_required_hours=0, preparation_instructions="No special preparation needed.", report_delivery_hours=6),
    LabTest(id=14, test_code="LAB-DENGUE", test_name="Dengue NS1 Antigen & Antibody Test", category="Serology / Virology", price=Decimal("3200.00"), fasting_required_hours=0, preparation_instructions="Recommended within 1-5 days of fever onset.", report_delivery_hours=3),
    LabTest(id=15, test_code="LAB-VITD", test_name="Vitamin D3 Total (25-OH)", category="Endocrinology", price=Decimal("5800.00"), fasting_required_hours=0, preparation_instructions="No fasting required. Inform lab if taking high-dose Vitamin D supplements.", report_delivery_hours=24),
    LabTest(id=16, test_code="LAB-VITB12", test_name="Vitamin B12 Level", category="Endocrinology", price=Decimal("4500.00"), fasting_required_hours=8, preparation_instructions="8-hour overnight fasting recommended.", report_delivery_hours=24),
    LabTest(id=17, test_code="LAB-THYROID", test_name="Full Thyroid Profile (FT3, FT4, TSH)", category="Endocrinology", price=Decimal("4800.00"), fasting_required_hours=0, preparation_instructions="Morning sample preferred. Do not take thyroid medication before sample collection.", report_delivery_hours=12),
    LabTest(id=18, test_code="LAB-PSA", test_name="Prostate Specific Antigen (Total PSA)", category="Tumor Markers", price=Decimal("3800.00"), fasting_required_hours=0, preparation_instructions="Avoid ejaculation and vigorous exercise 48 hours prior to blood test.", report_delivery_hours=24),
    LabTest(id=19, test_code="LAB-CRP", test_name="High Sensitivity C-Reactive Protein (hs-CRP)", category="Immunology", price=Decimal("2200.00"), fasting_required_hours=0, preparation_instructions="Used to assess cardiac risk and systemic inflammation.", report_delivery_hours=6),
    LabTest(id=20, test_code="LAB-TROP", test_name="Troponin I Quantitative (Cardiac Marker)", category="Cardiology / Emergency", price=Decimal("4500.00"), fasting_required_hours=0, preparation_instructions="Emergency cardiac biomarker for acute coronary syndrome.", report_delivery_hours=2),
    LabTest(id=21, test_code="LAB-CEA", test_name="Carcinoembryonic Antigen (CEA)", category="Tumor Markers", price=Decimal("4200.00"), fasting_required_hours=0, preparation_instructions="General cancer screening marker (gastrointestinal, lung, breast).", report_delivery_hours=24),
    LabTest(id=22, test_code="LAB-CA125", test_name="Cancer Antigen 125 (CA-125)", category="Tumor Markers", price=Decimal("4600.00"), fasting_required_hours=0, preparation_instructions="Ovarian health & cancer marker screening.", report_delivery_hours=24),
    LabTest(id=23, test_code="LAB-UCULT", test_name="Urine Culture & Antibiotic Sensitivity", category="Microbiology", price=Decimal("2100.00"), fasting_required_hours=0, preparation_instructions="Clean catch mid-stream urine. Sample must be collected before starting antibiotics.", report_delivery_hours=48),
    LabTest(id=24, test_code="LAB-ESR", test_name="Erythrocyte Sedimentation Rate (ESR)", category="Hematology", price=Decimal("600.00"), fasting_required_hours=0, preparation_instructions="General marker of inflammation.", report_delivery_hours=4),
    LabTest(id=25, test_code="LAB-LIPID-AD", test_name="Advanced Lipid & ApoB Profile", category="Cardiology", price=Decimal("5200.00"), fasting_required_hours=12, preparation_instructions="12-hour strict fasting. Measures LDL-C, HDL-C, Triglycerides, ApoB, and Lipoprotein(a).", report_delivery_hours=24),
]


HEALTH_PACKAGES = [
    HealthPackage(id=5, package_name="Starter Basic Health Screening", category="Preventive Health Check", price=Decimal("6450.00"), target_audience="Young adults (18-30 years)", included_tests_and_services="Full Blood Count, Fasting Blood Sugar, Urine Full Report, Body Mass Index (BMI) assessment, and Medical Officer consultation."),
    HealthPackage(id=6, package_name="Essential Health Check Package", category="Preventive Health Check", price=Decimal("10450.00"), target_audience="Adults seeking annual wellness check", included_tests_and_services="Full Blood Count, Fasting Blood Sugar, Lipid Profile, Urine Full Report, ECG, Serum Creatinine, and General Physician Consultation."),
    HealthPackage(id=7, package_name="Well Woman Package (Under 40)", category="Women Health", price=Decimal("25150.00"), target_audience="Females under 40 years", included_tests_and_services="FBC, FBS, Lipid Profile, Thyroid Profile (TSH), Pap Smear, Pelvic Ultrasound, Clinical Breast Examination, and Consultant Gynecologist consultation."),
    HealthPackage(id=8, package_name="Executive Female Screening (Above 40)", category="Women Health", price=Decimal("28850.00"), target_audience="Females 40 years and above", included_tests_and_services="Full Blood Count, FBS, HbA1c, Lipid Profile, Renal Profile, Mammogram / Breast Ultrasound, Pap Smear, Bone Density Screening, and Gynecologist consultation."),
    HealthPackage(id=9, package_name="Classic Male Health Package (Under 40)", category="Men Health", price=Decimal("30300.00"), target_audience="Males under 40 years", included_tests_and_services="Full Blood Count, FBS, Lipid Profile, Liver Function Test, Renal Function Test, ECG, Abdominal Ultrasound, and Physician Consultation."),
    HealthPackage(id=10, package_name="Standard Over 40 Men Package", category="Men Health", price=Decimal("38500.00"), target_audience="Males 40 years and above", included_tests_and_services="FBC, FBS, HbA1c, Lipid Profile, LFT, RFT, Total PSA (Prostate), ECG, Exercise Stress Test (TMT), Chest X-Ray, and Consultant Physician Consultation."),
    HealthPackage(id=11, package_name="Comprehensive Cancer Screening (Men)", category="Oncology / Preventive", price=Decimal("64900.00"), target_audience="Men over 45 or high risk", included_tests_and_services="CBC, Stool Occult Blood, Total PSA, CEA, AFP, Ultrasound Abdomen & Pelvis, Low-Dose CT Chest Screening, and Oncologist / Physician Review."),
    HealthPackage(id=12, package_name="Comprehensive Cancer Screening (Women)", category="Oncology / Preventive", price=Decimal("60700.00"), target_audience="Women over 40 or high risk", included_tests_and_services="CBC, Pap Smear, CA-125, CEA, Bilateral Digital Mammogram, Breast Ultrasound, Pelvic Ultrasound, Stool Occult Blood, and Specialist Review."),
    HealthPackage(id=13, package_name="Pre-Employment Medical Checkup", category="Occupational Health", price=Decimal("8500.00"), target_audience="Job Applicants & Employees", included_tests_and_services="Full Blood Count, Fasting Blood Sugar, Urine Full Report, Chest X-Ray (PA view), Blood Grouping & Rh, Vision Test, and Medical Fitness Certificate."),
    HealthPackage(id=14, package_name="Thyroid Care & Metabolic Screening", category="Endocrinology", price=Decimal("7800.00"), target_audience="Patients with fatigue or weight issues", included_tests_and_services="Free T3, Free T4, TSH, Fasting Blood Sugar, Lipid Profile, Thyroid Ultrasound Scan, and Endocrinologist Review."),
    HealthPackage(id=15, package_name="Pre-Marital Health Screening", category="Preventive / Reproductive", price=Decimal("16500.00"), target_audience="Couples planning marriage", included_tests_and_services="Full Blood Count, Blood Grouping & Rh, Thalassemia Screening (Hb Electrophoresis), Hepatitis B Surface Antigen, HIV I & II Screening, VDRL/RPR, and Genetic Counselor consultation."),
]


def seed_database():
    engine = get_database_engine()
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        for record in SPECIALTIES + DOCTORS + CHANNELING_SESSIONS + LAB_TESTS + HEALTH_PACKAGES:
            session.merge(record)
        session.commit()

    print("Database tables created and seed data inserted.")


if __name__ == "__main__":
    seed_database()
