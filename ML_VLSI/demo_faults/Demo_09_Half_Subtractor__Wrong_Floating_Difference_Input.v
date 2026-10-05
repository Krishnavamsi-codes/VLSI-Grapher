// Broken half subtractor for demonstration.
// Error: U1 should use b, but its B pin reads missing_b. Difference is therefore unreliable.
module half_subtractor_wrong_floating_difference (a, b, difference, borrow);
  input a, b;
  output difference, borrow;
  wire not_a, missing_b;

  XOR2_X1M_A9TH U1 (.A(a), .B(missing_b), .Y(difference));
  INV_X1M_A9TH  U2 (.A(a), .Y(not_a));
  AND2_X1M_A9TH U3 (.A(not_a), .B(b), .Y(borrow));
endmodule
