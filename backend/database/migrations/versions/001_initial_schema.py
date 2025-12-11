"""Initial database schema

Revision ID: 001
Revises: 
Create Date: 2024-11-03 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create students table
    op.create_table('students',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('student_id', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('student_type', sa.Enum('DAY_SCHOLAR', 'HOSTEL_STUDENT', name='studenttype'), nullable=False),
        sa.Column('face_embedding', sa.LargeBinary(), nullable=False),
        sa.Column('enrollment_date', sa.DateTime(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('phone', sa.String(length=20), nullable=True),
        sa.Column('class_id', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_students')),
        sa.UniqueConstraint('student_id', name=op.f('uq_students_student_id'))
    )
    op.create_index('ix_students_class_active', 'students', ['class_id', 'is_active'], unique=False)
    op.create_index('ix_students_type_active', 'students', ['student_type', 'is_active'], unique=False)
    op.create_index(op.f('ix_students_class_id'), 'students', ['class_id'], unique=False)
    op.create_index(op.f('ix_students_is_active'), 'students', ['is_active'], unique=False)
    op.create_index(op.f('ix_students_student_id'), 'students', ['student_id'], unique=False)
    op.create_index(op.f('ix_students_student_type'), 'students', ['student_type'], unique=False)

    # Create attendance_sessions table
    op.create_table('attendance_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', sa.String(length=100), nullable=False),
        sa.Column('class_id', sa.String(length=50), nullable=False),
        sa.Column('faculty_id', sa.String(length=50), nullable=False),
        sa.Column('start_time', sa.DateTime(), nullable=False),
        sa.Column('end_time', sa.DateTime(), nullable=True),
        sa.Column('total_registered', sa.Integer(), nullable=False),
        sa.Column('total_detected', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_attendance_sessions')),
        sa.UniqueConstraint('session_id', name=op.f('uq_attendance_sessions_session_id'))
    )
    op.create_index('ix_sessions_class_date', 'attendance_sessions', ['class_id', 'start_time'], unique=False)
    op.create_index('ix_sessions_faculty_date', 'attendance_sessions', ['faculty_id', 'start_time'], unique=False)
    op.create_index(op.f('ix_attendance_sessions_class_id'), 'attendance_sessions', ['class_id'], unique=False)
    op.create_index(op.f('ix_attendance_sessions_faculty_id'), 'attendance_sessions', ['faculty_id'], unique=False)
    op.create_index(op.f('ix_attendance_sessions_is_active'), 'attendance_sessions', ['is_active'], unique=False)
    op.create_index(op.f('ix_attendance_sessions_session_id'), 'attendance_sessions', ['session_id'], unique=False)
    op.create_index(op.f('ix_attendance_sessions_start_time'), 'attendance_sessions', ['start_time'], unique=False)

    # Create attendance_records table
    op.create_table('attendance_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('student_id', sa.String(length=50), nullable=False),
        sa.Column('session_id', sa.String(length=100), nullable=False),
        sa.Column('status', sa.Enum('PRESENT', 'ABSENT', 'LATE', 'INCOMPLETE', name='attendancestatus'), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('gate_entry_time', sa.DateTime(), nullable=True),
        sa.Column('classroom_entry_time', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['attendance_sessions.session_id'], name=op.f('fk_attendance_records_session_id_attendance_sessions')),
        sa.ForeignKeyConstraint(['student_id'], ['students.student_id'], name=op.f('fk_attendance_records_student_id_students')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_attendance_records'))
    )
    op.create_index('ix_attendance_session_status', 'attendance_records', ['session_id', 'status'], unique=False)
    op.create_index('ix_attendance_student_session', 'attendance_records', ['student_id', 'session_id'], unique=False)
    op.create_index('ix_attendance_timestamp', 'attendance_records', ['timestamp'], unique=False)
    op.create_index(op.f('ix_attendance_records_session_id'), 'attendance_records', ['session_id'], unique=False)
    op.create_index(op.f('ix_attendance_records_status'), 'attendance_records', ['status'], unique=False)
    op.create_index(op.f('ix_attendance_records_student_id'), 'attendance_records', ['student_id'], unique=False)
    op.create_index(op.f('ix_attendance_records_timestamp'), 'attendance_records', ['timestamp'], unique=False)

    # Create face_detections table
    op.create_table('face_detections',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('bounding_box', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('embedding', sa.LargeBinary(), nullable=False),
        sa.Column('liveness_score', sa.Float(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('camera_location', sa.Enum('GATE', 'CLASSROOM', name='cameralocation'), nullable=False),
        sa.Column('student_id', sa.String(length=50), nullable=True),
        sa.Column('session_id', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['student_id'], ['students.student_id'], name=op.f('fk_face_detections_student_id_students')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_face_detections'))
    )
    op.create_index('ix_detections_camera_time', 'face_detections', ['camera_location', 'timestamp'], unique=False)
    op.create_index('ix_detections_confidence', 'face_detections', ['confidence'], unique=False)
    op.create_index('ix_detections_liveness', 'face_detections', ['liveness_score'], unique=False)
    op.create_index('ix_detections_student_time', 'face_detections', ['student_id', 'timestamp'], unique=False)
    op.create_index(op.f('ix_face_detections_camera_location'), 'face_detections', ['camera_location'], unique=False)
    op.create_index(op.f('ix_face_detections_confidence'), 'face_detections', ['confidence'], unique=False)
    op.create_index(op.f('ix_face_detections_liveness_score'), 'face_detections', ['liveness_score'], unique=False)
    op.create_index(op.f('ix_face_detections_session_id'), 'face_detections', ['session_id'], unique=False)
    op.create_index(op.f('ix_face_detections_student_id'), 'face_detections', ['student_id'], unique=False)
    op.create_index(op.f('ix_face_detections_timestamp'), 'face_detections', ['timestamp'], unique=False)

    # Create emotion_results table
    op.create_table('emotion_results',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('student_id', sa.String(length=50), nullable=False),
        sa.Column('session_id', sa.String(length=100), nullable=False),
        sa.Column('emotion', sa.Enum('INTERESTED', 'BORED', 'CONFUSED', name='emotiontype'), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('engagement_score', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['attendance_sessions.session_id'], name=op.f('fk_emotion_results_session_id_attendance_sessions')),
        sa.ForeignKeyConstraint(['student_id'], ['students.student_id'], name=op.f('fk_emotion_results_student_id_students')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_emotion_results'))
    )
    op.create_index('ix_emotions_session_time', 'emotion_results', ['session_id', 'timestamp'], unique=False)
    op.create_index('ix_emotions_student_session', 'emotion_results', ['student_id', 'session_id'], unique=False)
    op.create_index('ix_emotions_type_confidence', 'emotion_results', ['emotion', 'confidence'], unique=False)
    op.create_index(op.f('ix_emotion_results_confidence'), 'emotion_results', ['confidence'], unique=False)
    op.create_index(op.f('ix_emotion_results_emotion'), 'emotion_results', ['emotion'], unique=False)
    op.create_index(op.f('ix_emotion_results_engagement_score'), 'emotion_results', ['engagement_score'], unique=False)
    op.create_index(op.f('ix_emotion_results_session_id'), 'emotion_results', ['session_id'], unique=False)
    op.create_index(op.f('ix_emotion_results_student_id'), 'emotion_results', ['student_id'], unique=False)
    op.create_index(op.f('ix_emotion_results_timestamp'), 'emotion_results', ['timestamp'], unique=False)

    # Create emotion_statistics table
    op.create_table('emotion_statistics',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', sa.String(length=100), nullable=False),
        sa.Column('total_frames', sa.Integer(), nullable=False),
        sa.Column('emotion_counts', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('emotion_percentages', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('average_engagement_score', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['attendance_sessions.session_id'], name=op.f('fk_emotion_statistics_session_id_attendance_sessions')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_emotion_statistics'))
    )
    op.create_index(op.f('ix_emotion_statistics_session_id'), 'emotion_statistics', ['session_id'], unique=False)

    # Create system_health table
    op.create_table('system_health',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('component', sa.String(length=100), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('metrics', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_system_health'))
    )
    op.create_index('ix_health_component_time', 'system_health', ['component', 'timestamp'], unique=False)
    op.create_index('ix_health_status_time', 'system_health', ['status', 'timestamp'], unique=False)
    op.create_index(op.f('ix_system_health_component'), 'system_health', ['component'], unique=False)
    op.create_index(op.f('ix_system_health_status'), 'system_health', ['status'], unique=False)
    op.create_index(op.f('ix_system_health_timestamp'), 'system_health', ['timestamp'], unique=False)

    # Create audit_logs table
    op.create_table('audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('resource_type', sa.String(length=50), nullable=False),
        sa.Column('resource_id', sa.String(length=100), nullable=False),
        sa.Column('user_id', sa.String(length=50), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_audit_logs'))
    )
    op.create_index('ix_audit_action_time', 'audit_logs', ['action', 'timestamp'], unique=False)
    op.create_index('ix_audit_resource_time', 'audit_logs', ['resource_type', 'timestamp'], unique=False)
    op.create_index('ix_audit_user_time', 'audit_logs', ['user_id', 'timestamp'], unique=False)
    op.create_index(op.f('ix_audit_logs_action'), 'audit_logs', ['action'], unique=False)
    op.create_index(op.f('ix_audit_logs_resource_id'), 'audit_logs', ['resource_id'], unique=False)
    op.create_index(op.f('ix_audit_logs_resource_type'), 'audit_logs', ['resource_type'], unique=False)
    op.create_index(op.f('ix_audit_logs_success'), 'audit_logs', ['success'], unique=False)
    op.create_index(op.f('ix_audit_logs_timestamp'), 'audit_logs', ['timestamp'], unique=False)
    op.create_index(op.f('ix_audit_logs_user_id'), 'audit_logs', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_table('audit_logs')
    op.drop_table('system_health')
    op.drop_table('emotion_statistics')
    op.drop_table('emotion_results')
    op.drop_table('face_detections')
    op.drop_table('attendance_records')
    op.drop_table('attendance_sessions')
    op.drop_table('students')
    op.execute('DROP TYPE IF EXISTS emotiontype')
    op.execute('DROP TYPE IF EXISTS cameralocation')
    op.execute('DROP TYPE IF EXISTS attendancestatus')
    op.execute('DROP TYPE IF EXISTS studenttype')