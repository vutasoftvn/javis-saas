import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../../core/widgets/app_modal_dialog.dart';
import '../../controllers/marketing_controller.dart';
import '../widgets/marketing_forms.dart';

void showContextForm(BuildContext context, MarketingController controller) {
  final ctx = controller.marketingContext;
  String textOf(String key) {
    final value = ctx[key];
    if (value == null) return '';
    if (value is Map && value['summary'] != null) return value['summary'].toString();
    if (value is Map || value is List) return '';
    return value.toString();
  }

  final icp = TextEditingController(text: textOf('icp'));
  final positioning = TextEditingController(text: textOf('positioning'));
  final valueProp = TextEditingController(text: textOf('value_proposition'));
  final brandVoice = TextEditingController(text: textOf('brand_voice'));
  final pricing = TextEditingController(text: textOf('pricing'));
  final constraints = TextEditingController(
    text: ((ctx['constraints'] as List<dynamic>?) ?? const []).join('\n'),
  );

  AppModalDialog.show<void>(
    context: context,
    title: 'Cập nhật bối cảnh Marketing',
    subtitle: 'COSA là nguồn sự thật duy nhất về bối cảnh; skill bên ngoài chỉ nhận gói tối thiểu.',
    icon: Icons.hub_outlined,
    maxWidth: 640,
    content: Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        marketingTextField(controller: icp, label: 'Chân dung khách hàng lý tưởng (ICP)', maxLines: 3),
        marketingTextField(controller: positioning, label: 'Tuyên bố định vị', maxLines: 3),
        marketingTextField(controller: valueProp, label: 'Tuyên ngôn giá trị', maxLines: 3),
        marketingTextField(controller: brandVoice, label: 'Giọng điệu thương hiệu', maxLines: 2),
        marketingTextField(controller: pricing, label: 'Chính sách giá', maxLines: 2),
        marketingTextField(
          controller: constraints,
          label: 'Ràng buộc (mỗi dòng một mục)',
          hint: 'VD: công ty một người\nngân sách hạn chế',
          maxLines: 3,
        ),
      ],
    ),
    actions: [
      marketingDialogActions(
        submitLabel: 'Lưu bối cảnh',
        onSubmit: () {
          Map<String, dynamic>? wrap(TextEditingController c) =>
              c.text.trim().isEmpty ? null : {'summary': c.text.trim()};

          Get.back<void>();
          controller.saveContext({
            'icp': wrap(icp),
            'positioning': wrap(positioning),
            'value_proposition': wrap(valueProp),
            'brand_voice': wrap(brandVoice),
            'pricing': wrap(pricing),
            'constraints': constraints.text.trim().isEmpty
                ? null
                : constraints.text.trim().split('\n').map((e) => e.trim()).where((e) => e.isNotEmpty).toList(),
          });
        },
      ),
    ],
  );
}

void showCustomerResearchForm(BuildContext context, MarketingController controller) {
  final current = controller.customerResearch;
  final segments = TextEditingController(text: (current['segments'] is List) ? (current['segments'] as List).join('\n') : (current['segments']?.toString() ?? ''));
  final jtbd = TextEditingController(text: (current['jtbd'] is List) ? (current['jtbd'] as List).join('\n') : (current['jtbd']?.toString() ?? ''));
  final pains = TextEditingController(text: (current['pains'] is List) ? (current['pains'] as List).join('\n') : (current['pains']?.toString() ?? ''));
  final facts = TextEditingController(text: (current['facts'] is List) ? (current['facts'] as List).join('\n') : (current['facts']?.toString() ?? ''));
  final hypotheses = TextEditingController(text: (current['hypotheses'] is List) ? (current['hypotheses'] as List).join('\n') : (current['hypotheses']?.toString() ?? ''));

  AppModalDialog.show<void>(
    context: context,
    title: 'Nghiên cứu Khách hàng (Customer Research)',
    subtitle: 'Phân loại kết luận theo FACT (sự thật kiểm chứng) và HYPOTHESIS (giả thuyết cần kiểm định) (§10).',
    icon: Icons.person_search_outlined,
    maxWidth: 620,
    content: Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        marketingTextField(controller: segments, label: 'Phân khúc khách hàng mục tiêu (mỗi dòng 1 phân khúc)', maxLines: 3),
        marketingTextField(controller: jtbd, label: 'Việc cần làm (Jobs-to-be-Done)', maxLines: 3),
        marketingTextField(controller: pains, label: 'Nỗi đau & Rào cản mua hàng (Pains & Objections)', maxLines: 3),
        marketingTextField(controller: facts, label: 'Sự thật đã kiểm chứng (FACTS)', maxLines: 3),
        marketingTextField(controller: hypotheses, label: 'Giả thuyết đang cần kiểm định (HYPOTHESES)', maxLines: 3),
      ],
    ),
    actions: [
      marketingDialogActions(
        submitLabel: 'Lưu nghiên cứu',
        onSubmit: () {
          List<String> toLines(TextEditingController c) =>
              c.text.trim().split('\n').map((e) => e.trim()).where((e) => e.isNotEmpty).toList();

          Get.back<void>();
          controller.saveCustomerResearch({
            'segments': toLines(segments),
            'jtbd': toLines(jtbd),
            'pains': toLines(pains),
            'facts': toLines(facts),
            'hypotheses': toLines(hypotheses),
          });
        },
      ),
    ],
  );
}

void showProductMarketingForm(BuildContext context, MarketingController controller) {
  final current = controller.productMarketing;
  final category = TextEditingController(text: current['category']?.toString() ?? '');
  final alternatives = TextEditingController(text: (current['alternatives'] is List) ? (current['alternatives'] as List).join('\n') : (current['alternatives']?.toString() ?? ''));
  final differentiators = TextEditingController(text: (current['differentiators'] is List) ? (current['differentiators'] as List).join('\n') : (current['differentiators']?.toString() ?? ''));
  final positioningStatement = TextEditingController(text: current['positioning_statement']?.toString() ?? '');

  AppModalDialog.show<void>(
    context: context,
    title: 'Product Marketing & Định vị (§11)',
    subtitle: 'Xác định rõ Category, giải pháp thay thế, điểm khác biệt độc bản và thông điệp.',
    icon: Icons.rocket_launch_outlined,
    maxWidth: 620,
    content: Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        marketingTextField(controller: category, label: 'Ngành hàng / Category', hint: 'VD: AI Marketing Operating System'),
        marketingTextField(controller: alternatives, label: 'Các giải pháp thay thế mà khách hàng đang dùng', maxLines: 3),
        marketingTextField(controller: differentiators, label: 'Điểm khác biệt độc bản (Differentiators)', maxLines: 3),
        marketingTextField(controller: positioningStatement, label: 'Tuyên bố định vị cốt lõi (Positioning Statement)', maxLines: 3),
      ],
    ),
    actions: [
      marketingDialogActions(
        submitLabel: 'Lưu định vị',
        onSubmit: () {
          List<String> toLines(TextEditingController c) =>
              c.text.trim().split('\n').map((e) => e.trim()).where((e) => e.isNotEmpty).toList();

          Get.back<void>();
          controller.saveProductMarketing({
            'category': category.text.trim(),
            'alternatives': toLines(alternatives),
            'differentiators': toLines(differentiators),
            'positioning_statement': positioningStatement.text.trim(),
          });
        },
      ),
    ],
  );
}

void showOfferArchitectureForm(BuildContext context, MarketingController controller) {
  final current = controller.offerArchitecture;
  final coreOffer = TextEditingController(text: current['core_offer']?.toString() ?? '');
  final value = TextEditingController(text: current['value']?.toString() ?? '');
  final proof = TextEditingController(text: current['proof']?.toString() ?? '');
  final bonus = TextEditingController(text: current['bonus']?.toString() ?? '');
  final guarantee = TextEditingController(text: current['guarantee']?.toString() ?? '');
  final urgency = TextEditingController(text: current['urgency']?.toString() ?? '');
  final cta = TextEditingController(text: current['cta']?.toString() ?? '');

  AppModalDialog.show<void>(
    context: context,
    title: 'Kiến trúc Ưu đãi (Offer Architecture §12)',
    subtitle: 'Thiết kế gói ưu đãi không thể từ chối: Core Offer + Value + Proof + Bonus + Guarantee + Urgency + CTA.',
    icon: Icons.local_offer_outlined,
    maxWidth: 620,
    content: Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        marketingTextField(controller: coreOffer, label: 'Ưu đãi cốt lõi (Core Offer)', hint: 'VD: 14 ngày dùng thử miễn phí đầy đủ tính năng'),
        marketingTextField(controller: value, label: 'Giá trị mang lại (Value)', maxLines: 2),
        marketingTextField(controller: proof, label: 'Bảo chứng & Bằng chứng (Proof)', maxLines: 2),
        marketingTextField(controller: bonus, label: 'Quà tặng kèm (Bonus / Add-ons)', maxLines: 2),
        marketingTextField(controller: guarantee, label: 'Cam kết đảo ngược rủi ro (Risk Reversal / Guarantee)', hint: 'VD: Hoàn tiền 100% trong 30 ngày nếu không hài lòng'),
        marketingTextField(controller: urgency, label: 'Yếu tố thúc đẩy / Khan hiếm (Urgency / Scarcity)', hint: 'VD: Dành cho 50 tài khoản đăng ký sớm'),
        marketingTextField(controller: cta, label: 'Lời kêu gọi hành động (Call to Action)', hint: 'VD: Bắt đầu dùng thử miễn phí ngay'),
      ],
    ),
    actions: [
      marketingDialogActions(
        submitLabel: 'Lưu kiến trúc ưu đãi',
        onSubmit: () {
          Get.back<void>();
          controller.saveOfferArchitecture({
            'core_offer': coreOffer.text.trim(),
            'value': value.text.trim(),
            'proof': proof.text.trim(),
            'bonus': bonus.text.trim(),
            'guarantee': guarantee.text.trim(),
            'urgency': urgency.text.trim(),
            'cta': cta.text.trim(),
          });
        },
      ),
    ],
  );
}
