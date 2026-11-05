#include <array>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>

int main(int argc, char **argv) {
    if (argc != 2) return 2;
    std::ifstream input(argv[1]);
    int n, k;
    long double beta, outside;
    if (!(input >> n >> k >> beta >> outside) || n != 9 || k != 6 || beta != 1000 || outside != 0) return 3;
    std::array<int, 9> market{};
    for (auto &a : market) if (!(input >> a) || a < 0 || a >= k) return 4;
    std::array<std::array<long double, 6>, 9> values{}, welfare{}, weights{};
    std::array<int, 9> component{};
    for (int i = 0; i < n; ++i) {
        for (int a = 0; a < k; ++a) {
            if (!(input >> values[i][a] >> welfare[i][a])) return 5;
            weights[i][a] = std::exp(beta * values[i][a]);
            if (!std::isfinite(weights[i][a]) || weights[i][a] <= 0) return 6;
            if (a && welfare[i][a] > welfare[i][component[i]]) component[i] = a;
        }
    }
    auto objective = [&](const std::array<int, 9> &profile) {
        long double numerator = outside * std::exp(beta * outside);
        long double denominator = std::exp(beta * outside);
        for (int i = 0; i < n; ++i) {
            numerator += weights[i][profile[i]] * welfare[i][profile[i]];
            denominator += weights[i][profile[i]];
        }
        return numerator / denominator;
    };
    std::array<int, 9> profile{}, best_profile{};
    long double best = -std::numeric_limits<long double>::infinity();
    unsigned long long count = 0;
    while (true) {
        const auto current = objective(profile);
        ++count;
        if (current > best) { best = current; best_profile = profile; }
        int i = n - 1;
        while (i >= 0 && ++profile[i] == k) { profile[i] = 0; --i; }
        if (i < 0) break;
    }
    if (count != 10077696ULL) return 7;
    std::cout << std::setprecision(22) << "long_double_precision_bits " << std::numeric_limits<long double>::digits
              << "\nprofiles " << count << "\nbest " << best
              << "\nmarket " << objective(market) << "\ncomponentwise " << objective(component) << "\nbest_actions";
    for (auto x : best_profile) std::cout << " " << x;
    std::cout << "\ncomponent_actions";
    for (auto x : component) std::cout << " " << x;
    std::cout << "\n";
}
