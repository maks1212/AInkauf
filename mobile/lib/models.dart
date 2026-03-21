class ParsedItem {
  final double quantity;
  final String unit;
  final String productName;

  ParsedItem({
    required this.quantity,
    required this.unit,
    required this.productName,
  });

  factory ParsedItem.fromJson(Map<String, dynamic> json) {
    return ParsedItem(
      quantity: (json['quantity'] as num).toDouble(),
      unit: json['unit'] as String,
      productName: json['product_name'] as String,
    );
  }
}

class DetourDecision {
  final bool isWorthIt;
  final double grossSavingsEur;
  final double fuelCostEur;
  final double netSavingsEur;
  final String explanation;

  DetourDecision({
    required this.isWorthIt,
    required this.grossSavingsEur,
    required this.fuelCostEur,
    required this.netSavingsEur,
    required this.explanation,
  });

  factory DetourDecision.fromJson(Map<String, dynamic> json) {
    return DetourDecision(
      isWorthIt: json['is_worth_it'] as bool,
      grossSavingsEur: (json['gross_savings_eur'] as num).toDouble(),
      fuelCostEur: (json['fuel_cost_eur'] as num).toDouble(),
      netSavingsEur: (json['net_savings_eur'] as num).toDouble(),
      explanation: json['explanation'] as String,
    );
  }
}
