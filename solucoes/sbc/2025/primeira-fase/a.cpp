#include <iostream>

using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, k;
    cin >> n >> k;

    // N falas e N - 1 intervalos de um minuto.
    cout << (k - (n - 1)) / n << '\n';
    return 0;
}
