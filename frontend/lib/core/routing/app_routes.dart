abstract class AppRoutes {
  static const initial = '/';
  static const login = '/login';
  static const register = '/register';
  static const projectsNew = '/projects/new';
  static const companyPicker = '/company-picker'; // Deprecated, kept for compatibility
  static const workspacePicker = '/workspace-picker';
  
  // COSA 5+1 Core Routes (§b1, §P0.6)
  static const hub = '/hub';
  static const chat = '/chat';
  static const work = '/work';
  static const company = '/company';
  static const brain = '/brain';
  static const admin = '/admin';
  static const profile = '/profile';

  // Feature Modules Routes
  // Task 9 — các hằng số path bên dưới (approvals/agents/tasks/vault/
  // strategy/sales/marketing/finance/legal/workflows) giờ chỉ còn dùng làm
  // NGUỒN cho route redirect legacy (xem `LegacyModuleRedirectMiddleware`
  // trong `module_routes.dart`) — route thật, đang guard bởi AuthMiddleware,
  // nằm ở `WorkspaceModule.<module>.path` (namespace `/work/*`). Giữ nguyên
  // các hằng số này để không phá deep-link/bookmark cũ.
  static const approvals = '/approvals';
  static const agents = '/agents';
  static const tasks = '/tasks';
  static const dashboard = '/dashboard';
  static const vault = '/vault';
  static const strategy = '/strategy';
  static const missionControl = '/mission-control';
  static const sales = '/sales';
  static const marketing = '/marketing';
  static const finance = '/finance';
  static const legal = '/legal';
  static const workflows = '/workflows';
}
