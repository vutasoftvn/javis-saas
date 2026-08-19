import 'package:flutter/material.dart';
import '../../../data/models/workforce_pack_model.dart';

class AiWorkforceTab extends StatelessWidget {
  final List<WorkforcePackModel> packs;
  final Function(String packKey, bool value) onTogglePack;

  const AiWorkforceTab({
    super.key,
    required this.packs,
    required this.onTogglePack,
  }) : super();

  @override
  Widget build(BuildContext context) {
    final coreDomains = packs.where((p) => p.isCore).toList();
    final optionalPacks = packs.where((p) => !p.isCore).toList();

    return LayoutBuilder(
      builder: (context, constraints) {
        final isWide = constraints.maxWidth >= 900;
        final coreCols = isWide ? 3 : 2;

        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // 1. Core Domains Section
            Row(
              children: [
                const Icon(Icons.hub, color: Color(0xFF6366F1), size: 20),
                const SizedBox(width: 8),
                const Text(
                  '5 CORE DOMAIN WORKFORCE (Luôn kích hoạt)',
                  style: TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.bold,
                    color: Colors.white,
                    letterSpacing: 0.5,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 14),
            GridView.builder(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                crossAxisCount: coreCols,
                crossAxisSpacing: 14,
                mainAxisSpacing: 14,
                childAspectRatio: isWide ? 2.0 : 1.5,
              ),
              itemCount: coreDomains.length,
              itemBuilder: (context, index) {
                final pack = coreDomains[index];
                return _buildDomainCard(pack);
              },
            ),
            const SizedBox(height: 32),

            // 2. Optional Packs Store Section
            Row(
              children: [
                const Icon(Icons.storefront_outlined, color: Color(0xFF10B981), size: 20),
                const SizedBox(width: 8),
                const Text(
                  'OPTIONAL PACKS STORE (Bật theo quy mô)',
                  style: TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.bold,
                    color: Colors.white,
                    letterSpacing: 0.5,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 14),
            if (isWide)
              GridView.builder(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                  crossAxisCount: 2,
                  crossAxisSpacing: 14,
                  mainAxisSpacing: 14,
                  childAspectRatio: 3.2,
                ),
                itemCount: optionalPacks.length,
                itemBuilder: (context, index) {
                  return _buildOptionalPackItem(optionalPacks[index]);
                },
              )
            else
              ...optionalPacks.map((p) => _buildOptionalPackItem(p)),
          ],
        );
      },
    );
  }

  Widget _buildDomainCard(WorkforcePackModel pack) {
    IconData icon;
    Color color;

    if (pack.key.contains('sales')) {
      icon = Icons.trending_up;
      color = const Color(0xFF10B981);
    } else if (pack.key.contains('cmo') || pack.key.contains('marketing')) {
      icon = Icons.campaign;
      color = const Color(0xFFEC4899);
    } else if (pack.key.contains('cfo') || pack.key.contains('finance')) {
      icon = Icons.account_balance;
      color = const Color(0xFFF59E0B);
    } else if (pack.key.contains('legal')) {
      icon = Icons.gavel;
      color = const Color(0xFF8B5CF6);
    } else {
      icon = Icons.code;
      color = const Color(0xFF3B82F6);
    }

    return Container(
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: color.withValues(alpha: 0.4), width: 1.2),
      ),
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(6),
                decoration: BoxDecoration(
                  color: color.withValues(alpha: 0.15),
                  shape: BoxShape.circle,
                ),
                child: Icon(icon, color: color, size: 18),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      pack.name,
                      style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.white, fontSize: 13),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                    Text(
                      pack.roleTitle ?? 'Domain Agent',
                      style: TextStyle(color: Colors.white.withValues(alpha: 0.5), fontSize: 11),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ],
                ),
              ),
              Container(
                width: 8,
                height: 8,
                decoration: const BoxDecoration(
                  color: Color(0xFF10B981),
                  shape: BoxShape.circle,
                ),
              ),
            ],
          ),
          const Spacer(),
          Text(
            pack.description ?? '',
            style: TextStyle(color: Colors.white.withValues(alpha: 0.7), fontSize: 11, height: 1.3),
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
          ),
        ],
      ),
    );
  }

  Widget _buildOptionalPackItem(WorkforcePackModel pack) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: const Color(0xFF334155)),
      ),
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: const Color(0xFF6366F1).withValues(alpha: 0.15),
              borderRadius: BorderRadius.circular(8),
            ),
            child: const Icon(Icons.extension_outlined, color: Color(0xFFA5B4FC), size: 20),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Row(
                  children: [
                    Text(
                      pack.name,
                      style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.white, fontSize: 14),
                    ),
                    const SizedBox(width: 8),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(
                        color: const Color(0xFF475569),
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: Text(
                        pack.department ?? 'Optional',
                        style: const TextStyle(color: Colors.white70, fontSize: 10),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 3),
                Text(
                  pack.description ?? '',
                  style: TextStyle(color: Colors.white.withValues(alpha: 0.65), fontSize: 11.5),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ),
          ),
          const SizedBox(width: 12),
          Switch(
            value: pack.isActive,
            onChanged: (val) => onTogglePack(pack.key, val),
            activeThumbColor: const Color(0xFF10B981),
            activeTrackColor: const Color(0xFF10B981).withValues(alpha: 0.3),
            inactiveThumbColor: Colors.white38,
            inactiveTrackColor: const Color(0xFF334155),
          ),
        ],
      ),
    );
  }
}
