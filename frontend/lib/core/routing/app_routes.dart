abstract class AppRoutes {
  static const initial = '/';
  static const login = '/login';
  static const register = '/register';
  static const companyPicker = '/company-picker';
  
  // COSA 5+1 Core Routes (§b1, §P0.6)
  static const hub = '/hub';
  static const chat = '/chat';
  static const work = '/work';
  static const company = '/company';
  static const brain = '/brain';
  static const admin = '/admin';
  static const profile = '/profile';

  // Feature Modules Routes
  static const approvals = '/approvals';
  static const agents = '/agents';
  static const tasks = '/tasks';
  static const dashboard = '/dashboard';
  static const vault = '/vault';
  static const strategy = '/strategy';
  static const missionControl = '/mission-control';
}
