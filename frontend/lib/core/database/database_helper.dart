import 'package:sqflite/sqflite.dart';
import 'package:path/path.dart';

class DatabaseHelper {
  static final DatabaseHelper instance = DatabaseHelper._init();

  static Database? _database;

  DatabaseHelper._init();

  Future<Database> get database async {
    if (_database != null) return _database!;

    _database = await _initDB('javis_cache.db');
    return _database!;
  }

  Future<Database> _initDB(String filePath) async {
    final dbPath = await getDatabasesPath();
    final path = join(dbPath, filePath);

    return await openDatabase(
      path,
      version: 1,
      onCreate: _createDB,
    );
  }

  Future _createDB(Database db, int version) async {
    await db.execute('''
      CREATE TABLE cached_tasks (
        id TEXT PRIMARY KEY,
        workspace_id TEXT,
        title TEXT,
        status TEXT,
        priority TEXT,
        planned_start_at TEXT,
        due_at TEXT,
        timezone TEXT,
        assignee_id TEXT,
        source TEXT,
        completion_policy TEXT,
        created_at TEXT,
        updated_at TEXT,
        sync_status TEXT DEFAULT 'synced' -- 'synced', 'pending_create', 'pending_update', 'pending_delete'
      )
    ''');

    await db.execute('''
      CREATE TABLE cached_task_dependencies (
        id TEXT PRIMARY KEY,
        task_id TEXT,
        depends_on_task_id TEXT,
        sync_status TEXT DEFAULT 'synced'
      )
    ''');

    await db.execute('''
      CREATE TABLE cached_task_schedules (
        id TEXT PRIMARY KEY,
        task_id TEXT,
        schedule_type TEXT,
        cron_expr TEXT,
        next_run_at TEXT,
        active INTEGER DEFAULT 1,
        sync_status TEXT DEFAULT 'synced'
      )
    ''');

    await db.execute('''
      CREATE TABLE task_client_outbox (
        id TEXT PRIMARY KEY,
        entity_type TEXT, -- 'task', 'dependency', 'schedule'
        entity_id TEXT,
        action TEXT, -- 'create', 'update', 'delete'
        payload TEXT, -- JSON payload
        created_at TEXT
      )
    ''');
    
    // Chat schema
    await db.execute('''
      CREATE TABLE cached_chat_sessions (
        id TEXT PRIMARY KEY,
        brain_id TEXT,
        title TEXT,
        last_message_at TEXT,
        created_at TEXT,
        sync_status TEXT DEFAULT 'synced'
      )
    ''');
    
    await db.execute('''
      CREATE TABLE cached_chat_messages (
        id TEXT PRIMARY KEY,
        session_id TEXT,
        role TEXT,
        content TEXT,
        status TEXT,
        client_message_id TEXT UNIQUE,
        created_at TEXT,
        sync_status TEXT DEFAULT 'synced'
      )
    ''');

    await db.execute('''
      CREATE TABLE chat_client_outbox (
        id TEXT PRIMARY KEY,
        session_id TEXT,
        client_message_id TEXT,
        payload TEXT,
        created_at TEXT
      )
    ''');
    
    // Strategy & OKR schema (Phase 2B)
    await db.execute('''
      CREATE TABLE cached_bsc_scorecards (
        id TEXT PRIMARY KEY,
        workspace_id TEXT,
        status TEXT,
        period_start TEXT,
        period_end TEXT,
        sync_status TEXT DEFAULT 'synced'
      )
    ''');
    
    await db.execute('''
      CREATE TABLE cached_strategic_objectives (
        id TEXT PRIMARY KEY,
        workspace_id TEXT,
        scorecard_id TEXT,
        perspective TEXT,
        statement TEXT,
        status TEXT,
        sync_status TEXT DEFAULT 'synced'
      )
    ''');
    
    await db.execute('''
      CREATE TABLE cached_okr_objectives (
        id TEXT PRIMARY KEY,
        workspace_id TEXT,
        title TEXT,
        status TEXT,
        sync_status TEXT DEFAULT 'synced'
      )
    ''');
    
    await db.execute('''
      CREATE TABLE cached_key_results (
        id TEXT PRIMARY KEY,
        workspace_id TEXT,
        objective_id TEXT,
        current_value REAL,
        target_value REAL,
        status TEXT,
        sync_status TEXT DEFAULT 'synced'
      )
    ''');
    
    await db.execute('''
      CREATE TABLE cached_twelve_week_cycles (
        id TEXT PRIMARY KEY,
        workspace_id TEXT,
        theme TEXT,
        status TEXT,
        sync_status TEXT DEFAULT 'synced'
      )
    ''');
    
    await db.execute('''
      CREATE TABLE cached_weekly_commitments (
        id TEXT PRIMARY KEY,
        workspace_id TEXT,
        title TEXT,
        status TEXT,
        sync_status TEXT DEFAULT 'synced'
      )
    ''');
  }

  Future<void> close() async {
    final db = await instance.database;
    db.close();
  }
}
