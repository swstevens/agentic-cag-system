"""
Deck Analyzer Service

Advanced deck analysis including:
- Mana curve analysis
- Land ratios
- Color distribution
- Combo detection
- Archetype consistency
"""

from typing import Dict, Any, List, Tuple
from collections import Counter


class DeckAnalyzer:
    """
    Analyze deck construction quality beyond basic legality
    """

    # Archetype-specific recommendations
    ARCHETYPE_CURVES = {
        'aggro': {
            'ideal_avg_cmc': (1.5, 2.5),
            'land_ratio': (0.30, 0.40),  # 30-40% lands
            'curve_focus': [1, 2, 3]  # Focus on 1-3 CMC
        },
        'midrange': {
            'ideal_avg_cmc': (2.5, 3.5),
            'land_ratio': (0.38, 0.45),  # 38-45% lands
            'curve_focus': [2, 3, 4]
        },
        'control': {
            'ideal_avg_cmc': (2.5, 4.0),
            'land_ratio': (0.40, 0.48),  # 40-48% lands
            'curve_focus': [2, 3, 4, 5]
        },
        'combo': {
            'ideal_avg_cmc': (2.0, 3.5),
            'land_ratio': (0.35, 0.42),
            'curve_focus': [1, 2, 3, 4]
        }
    }

    @staticmethod
    def analyze_full_deck(cards: List[Dict[str, Any]], archetype: str = 'midrange') -> Dict[str, Any]:
        """
        Comprehensive deck analysis

        Args:
            cards: List of card dictionaries
            archetype: Deck archetype (aggro, control, midrange, combo)

        Returns:
            Dictionary with complete analysis
        """
        analysis = {
            'deck_size': len(cards),
            'mana_curve': DeckAnalyzer.analyze_mana_curve(cards, archetype),
            'land_ratio': DeckAnalyzer.analyze_land_ratio(cards, archetype),
            'color_distribution': DeckAnalyzer.analyze_colors(cards),
            'card_types': DeckAnalyzer.analyze_card_types(cards),
            'combos': DeckAnalyzer.detect_combos(cards),
            'recommendations': []
        }

        # Generate recommendations
        analysis['recommendations'] = DeckAnalyzer._generate_recommendations(analysis, archetype)

        # Overall score
        analysis['overall_score'] = DeckAnalyzer._calculate_score(analysis)

        return analysis

    @staticmethod
    def analyze_mana_curve(cards: List[Dict[str, Any]], archetype: str = 'midrange') -> Dict[str, Any]:
        """
        Analyze mana curve distribution

        Returns:
            Mana curve statistics and evaluation
        """
        # Count cards by CMC
        curve = {i: 0 for i in range(8)}  # 0-7+
        total_nonland = 0

        for card in cards:
            if 'Land' not in card.get('type_line', ''):
                cmc = int(card.get('cmc', 0))
                if cmc >= 7:
                    curve[7] += 1
                else:
                    curve[cmc] += 1
                total_nonland += 1

        # Calculate average CMC
        total_cmc = sum(cmc * count for cmc, count in curve.items())
        avg_cmc = total_cmc / total_nonland if total_nonland > 0 else 0

        # Get archetype expectations
        arch_data = DeckAnalyzer.ARCHETYPE_CURVES.get(archetype, DeckAnalyzer.ARCHETYPE_CURVES['midrange'])
        ideal_min, ideal_max = arch_data['ideal_avg_cmc']
        focus_cmcs = arch_data['curve_focus']

        # Evaluate curve quality
        curve_quality = "good"
        if avg_cmc < ideal_min:
            curve_quality = "too_low"
        elif avg_cmc > ideal_max:
            curve_quality = "too_high"

        # Check if curve is concentrated in right spots
        focus_count = sum(curve[cmc] for cmc in focus_cmcs)
        focus_percentage = (focus_count / total_nonland * 100) if total_nonland > 0 else 0

        return {
            'curve': curve,
            'average_cmc': round(avg_cmc, 2),
            'total_nonland': total_nonland,
            'curve_quality': curve_quality,
            'focus_percentage': round(focus_percentage, 1),
            'focus_cmcs': focus_cmcs,
            'ideal_range': (ideal_min, ideal_max)
        }

    @staticmethod
    def analyze_land_ratio(cards: List[Dict[str, Any]], archetype: str = 'midrange') -> Dict[str, Any]:
        """
        Analyze land to non-land ratio

        Returns:
            Land ratio statistics and evaluation
        """
        total = len(cards)
        land_count = 0
        nonland_count = 0

        lands = []
        for card in cards:
            if 'Land' in card.get('type_line', ''):
                land_count += 1
                lands.append(card['name'])
            else:
                nonland_count += 1

        land_ratio = land_count / total if total > 0 else 0

        # Get archetype expectations
        arch_data = DeckAnalyzer.ARCHETYPE_CURVES.get(archetype, DeckAnalyzer.ARCHETYPE_CURVES['midrange'])
        ideal_min, ideal_max = arch_data['land_ratio']

        # Evaluate
        ratio_quality = "good"
        if land_ratio < ideal_min:
            ratio_quality = "too_few_lands"
        elif land_ratio > ideal_max:
            ratio_quality = "too_many_lands"

        return {
            'land_count': land_count,
            'nonland_count': nonland_count,
            'land_ratio': round(land_ratio, 3),
            'land_percentage': round(land_ratio * 100, 1),
            'ratio_quality': ratio_quality,
            'ideal_range': (ideal_min, ideal_max),
            'ideal_percentage': (ideal_min * 100, ideal_max * 100),
            'lands': list(set(lands))  # Unique land names
        }

    @staticmethod
    def analyze_colors(cards: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze color distribution

        Returns:
            Color statistics
        """
        color_counts = Counter()
        color_identity = set()

        for card in cards:
            colors = card.get('colors', [])
            for color in colors:
                color_counts[color] += 1
                color_identity.add(color)

        # Calculate color concentration
        total_colored = sum(color_counts.values())
        color_distribution = {
            color: round(count / total_colored * 100, 1) if total_colored > 0 else 0
            for color, count in color_counts.items()
        }

        return {
            'color_identity': sorted(color_identity),
            'color_counts': dict(color_counts),
            'color_distribution': color_distribution,
            'num_colors': len(color_identity),
            'is_monocolor': len(color_identity) == 1,
            'is_colorless': len(color_identity) == 0
        }

    @staticmethod
    def analyze_card_types(cards: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze card type distribution

        Returns:
            Card type statistics
        """
        type_counts = Counter()

        for card in cards:
            type_line = card.get('type_line', '')

            # Categorize by primary type
            if 'Creature' in type_line:
                type_counts['Creature'] += 1
            elif 'Instant' in type_line:
                type_counts['Instant'] += 1
            elif 'Sorcery' in type_line:
                type_counts['Sorcery'] += 1
            elif 'Enchantment' in type_line:
                type_counts['Enchantment'] += 1
            elif 'Artifact' in type_line:
                type_counts['Artifact'] += 1
            elif 'Planeswalker' in type_line:
                type_counts['Planeswalker'] += 1
            elif 'Land' in type_line:
                type_counts['Land'] += 1

        total = len(cards)
        type_percentages = {
            card_type: round(count / total * 100, 1) if total > 0 else 0
            for card_type, count in type_counts.items()
        }

        return {
            'type_counts': dict(type_counts),
            'type_percentages': type_percentages
        }

    @staticmethod
    def detect_combos(cards: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Detect potential combos in deck

        Returns:
            List of detected combos with explanations
        """
        combos = []

        # Build card name set for fast lookup
        card_names = {card['name'].lower() for card in cards}

        # Known combo patterns (simplified - could be much more extensive)
        COMBO_PATTERNS = [
            {
                'name': 'Splinter Twin Combo',
                'cards': ['splinter twin', 'deceiver exarch'],
                'description': 'Infinite creature tokens with haste'
            },
            {
                'name': 'Storm Combo',
                'cards': ['grapeshot', 'past in flames'],
                'description': 'Storm finisher with flashback recursion'
            },
            {
                'name': 'Empty the Warrens Storm',
                'cards': ['empty the warrens', 'rift bolt'],
                'description': 'Generate massive goblin tokens with storm'
            }
        ]

        for pattern in COMBO_PATTERNS:
            required_cards = pattern['cards']
            if all(card in card_names for card in required_cards):
                combos.append({
                    'name': pattern['name'],
                    'cards': required_cards,
                    'description': pattern['description']
                })

        # Detect synergy patterns (not full combos but strong interactions)
        synergies = DeckAnalyzer._detect_synergies(cards)

        return {
            'combos': combos,
            'synergies': synergies,
            'total_combos': len(combos),
            'total_synergies': len(synergies)
        }

    @staticmethod
    def _detect_synergies(cards: List[Dict[str, Any]]) -> List[str]:
        """
        Detect synergistic patterns

        Returns:
            List of synergy descriptions
        """
        synergies = []
        card_names = [card['name'].lower() for card in cards]

        # Check for prowess synergies
        has_prowess = any('prowess' in card.get('oracle_text', '').lower() for card in cards)
        has_many_spells = sum(1 for card in cards if 'Instant' in card.get('type_line', '') or 'Sorcery' in card.get('type_line', '')) > 15

        if has_prowess and has_many_spells:
            synergies.append("Prowess creatures with high spell density")

        # Check for burn synergies
        has_spectacle = any('spectacle' in card.get('oracle_text', '').lower() for card in cards)
        has_burn = any('damage' in card.get('oracle_text', '').lower() for card in cards)

        if has_spectacle and has_burn:
            synergies.append("Spectacle cards with burn spells")

        return synergies

    @staticmethod
    def _generate_recommendations(analysis: Dict[str, Any], archetype: str) -> List[str]:
        """
        Generate recommendations based on analysis

        Returns:
            List of recommendation strings
        """
        recommendations = []

        # Mana curve recommendations
        curve = analysis['mana_curve']
        if curve['curve_quality'] == 'too_low':
            recommendations.append(f"Average CMC ({curve['average_cmc']}) is too low. Consider adding more impactful cards in the {curve['ideal_range'][0]}-{curve['ideal_range'][1]} CMC range.")
        elif curve['curve_quality'] == 'too_high':
            recommendations.append(f"Average CMC ({curve['average_cmc']}) is too high. Consider adding more early game plays.")

        # Land ratio recommendations
        land = analysis['land_ratio']
        if land['ratio_quality'] == 'too_few_lands':
            recommended = int(analysis['deck_size'] * sum(land['ideal_range']) / 2)
            recommendations.append(f"Only {land['land_count']} lands ({land['land_percentage']}%). Consider adding {recommended - land['land_count']} more lands.")
        elif land['ratio_quality'] == 'too_many_lands':
            recommended = int(analysis['deck_size'] * sum(land['ideal_range']) / 2)
            recommendations.append(f"Too many lands ({land['land_count']}). Consider reducing to around {recommended} lands.")

        # Color distribution recommendations
        colors = analysis['color_distribution']
        if colors['num_colors'] > 2:
            recommendations.append(f"Running {colors['num_colors']} colors. Ensure mana base supports color requirements.")

        return recommendations

    @staticmethod
    def _calculate_score(analysis: Dict[str, Any]) -> float:
        """
        Calculate overall deck construction score (0-100)

        Returns:
            Score from 0-100
        """
        score = 100.0

        # Penalize mana curve issues
        if analysis['mana_curve']['curve_quality'] != 'good':
            score -= 15

        # Penalize land ratio issues
        if analysis['land_ratio']['ratio_quality'] != 'good':
            score -= 20

        # Bonus for combos/synergies
        score += min(analysis['combos']['total_combos'] * 5, 10)
        score += min(analysis['combos']['total_synergies'] * 3, 10)

        return max(0, min(100, score))
